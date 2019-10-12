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

from . import utils
from . import exceptions
from dataclasses import dataclass
from pathlib import Path
from typing import List, Union
import json
import re
import subprocess


@dataclass(frozen=True)
class PulumiResource:
    # TODO: requires documentation
    id: str
    urn: str
    type: str
    inputs: dict
    outputs: dict
    parent: Union[str, None]
    provider: str
    dependencies: dict


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
    def resources(self) -> List[PulumiResource]:
        resources = []

        state_resources = self.current["checkpoint"]["latest"].get("resources", [])

        regex = re.compile('pulumi:.+:.+')

        for i in state_resources:
            resource_type = i["type"]
            if regex.match(resource_type):
                continue

            pulumi_resource = PulumiResource(
                id           = i["id"],
                urn          = i["urn"],
                type         = i["type"],
                inputs       = i.get("inputs", {}),
                outputs      = i.get("outputs", {}),
                parent       = i.get("parent", None),
                provider     = i["provider"],
                dependencies = i.get("propertyDependencies", {})
            )
            resources.append(pulumi_resource)

        return resources

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
