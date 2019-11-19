# Copyright 2019 Ali (@bincyber)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations
from . import utils
from . import exceptions
from anytree import NodeMixin, RenderTree, AbstractStyle, ContStyle, findall_by_attr
from anytree.exporter import DotExporter
from dataclasses import dataclass, field
from os import PathLike
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union
import json
import subprocess


class PulumiResource(NodeMixin):
    def __init__(self,
        urn: str, rtype: str, rid: str, provider: str = None,
        inputs: dict = None, outputs: dict = None, dependencies: dict = None,
        parent: Union['PulumiResource', None] = None
    ) -> None:
        super().__init__()

        self.urn          = urn
        self.type         = rtype
        self.id           = rid
        self.provider     = provider
        self.inputs       = inputs
        self.outputs      = outputs
        self.dependencies = dependencies
        self.parent       = parent

    def __repr__(self):
        s = "PulumiResource(urn=%r, rtype=%r, rid=%r, provider=%r, inputs=%r, outputs=%r, dependencies=%r, parent=%r)" % (self.urn, self.type, self.id, self.provider, self.inputs, self.outputs, self.dependencies, self.parent)
        return s


@dataclass
class PulumiResources:
    # TODO: requires documentation
    items: List[PulumiResource] = field(default_factory=list)

    def __post_init__(self):
        self._providers = {}
        self._types     = {}

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, index):
        return self.items[index]

    def __iter__(self):
        self.n = 0
        return self

    def __next__(self):
        if self.n < len(self):
            i = self.items[self.n]
            self.n += 1
            return i
        else:
            raise StopIteration

    def append(self, obj) -> None:
        self.items.append(obj)

    def lookup(self, key: str, value: Any) -> Union[Tuple[PulumiResource, ...], Tuple[()]]:
        """ lookup resources by searching using a key (ie. id, urn, provider, type) and value """
        return findall_by_attr(self.items[0], name=key, value=value)

    def __find_root_node(self, node: PulumiResource):
        """ returns the root node of the resources tree """
        if node.is_root:
            return node
        else:
            return self.__find_root_node(node.parent)

    def __format_node_name(self, node: PulumiResource) -> str:
        """ formats the node name to 'node.type (node.id)' """
        s = node.type
        if node.id:
            s += f" ({node.id})"
        return s

    def render_tree(self, style: AbstractStyle = ContStyle) -> None:
        """ renders the resources tree in the style set by `style`. Defaults to anytree's ContStyle """
        root = self.__find_root_node(self.items[0])
        print(RenderTree(root, style=ContStyle).by_attr(self.__format_node_name))

    def export_dotfile(self, filename: PathLike = None) -> None:
        """ exports the resources tree as a DOT file to the file specified by `filename`. Defaults to graph.dot in the local directory otherwise """
        if filename is None:
            filename = Path.cwd().joinpath('graph.dot')
        else:
            filename = Path(filename).expanduser().absolute()

        root = self.__find_root_node(self.items[0])
        DotExporter(root, nodenamefunc=self.__format_node_name).to_dotfile(filename)

    @property
    def types(self) -> Dict[str, int]:
        """ returns a dictionary of resource types and their count of resources """
        if len(self._types):
            return self._types

        for i in self.items:
            self._types[i.type] = self._types.setdefault(i.type, 0) + 1

        return self._types

    @property
    def providers(self) -> Dict[str, int]:
        """ returns a dictionary of resource providers and their count of resources """
        if len(self._providers):
            return self._providers

        for i in self.items:
            if i.provider:
                provider = i.provider.split("::")[2]
                self._providers[provider] = self._providers.setdefault(provider, 0) + 1

        return self._providers


@dataclass
class PulumiState:
    # TODO: requires documentation
    stack: str
    encryptionsalt: str
    version: int = 3

    def __post_init__(self) -> None:
        timestamp = utils.get_current_timestamp()

        self.new = {
            'version': self.version,
            'checkpoint': {
                'stack': self.stack,
                'latest': {
                    'manifest': {
                        'time': timestamp,
                        'magic': self.magic_cookie,
                        'version': self.pulumi_version
                    },
                    'secrets_provider': {
                        'type': 'passphrase',
                        'state': {
                            'salt': self.encryptionsalt
                        }
                    }
                }
            }
        }

    def to_json(self) -> str:
        return json.dumps(self.current, indent=4)

    def write(self) -> None:
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        self.filepath.write_text(self.to_json())

    @property
    def dirpath(self) -> Path:
        return Path.cwd().joinpath('.pulumi')

    @property
    def filepath(self) -> Path:
        return self.dirpath.joinpath(f'stacks/{self.stack}.json')

    @property
    def pulumi_version(self) -> str:
        pulumi_binary = utils.find_pulumi_binary()
        cmd           = [pulumi_binary, 'version']

        process = subprocess.run(cmd, capture_output=True)

        stdout = utils.decode_utf8(process.stdout)

        if process.returncode != 0:
            err = stdout
            if len(err) == 0:
                err = utils.decode_utf8(process.stderr)
            raise exceptions.PulumiVersionExecError(err)

        return stdout.strip('\n')

    @property
    def magic_cookie(self) -> str:
        return utils.sha256sum(self.pulumi_version.encode('utf-8'))

    @property
    def resources(self) -> PulumiResources:
        pulumi_resources = PulumiResources()

        state_resources = self.current["checkpoint"]["latest"].get("resources", [])

        for i in state_resources:
            urn        = i["urn"]
            rtype      = i["type"]
            provider   = i.get("provider")
            parent_urn = i.get("parent")

            pulumi_resource = PulumiResource(
                urn          = urn,
                rtype        = rtype,
                rid          = i.get("id"),
                inputs       = i.get("inputs", {}),
                outputs      = i.get("outputs", {}),
                provider     = provider,
                dependencies = i.get("propertyDependencies", {})
            )

            if parent_urn is not None:
                results = pulumi_resources.lookup(key="urn", value=parent_urn)
                if results:
                    pulumi_resource.parent = results[0]

            pulumi_resources.append(pulumi_resource)

        return pulumi_resources

    @property
    def current(self) -> dict:
        """ retrieve the current state from the file """
        contents = self.new

        if self.filepath.exists():
            contents = json.loads(self.filepath.read_text())

        return contents

    @property
    def previous(self) -> dict:
        """ retrieve the previous state from the file """
        backups_directory = self.dirpath.joinpath(f'backups/{self.stack}')

        state_files = sorted(list(backups_directory.glob('*.json')))

        if len(state_files) > 1:
            previous_state_file, _  = state_files[-2:]

            contents = json.loads(previous_state_file.read_text())
        else:
            contents = self.new

        return contents
