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
from .config import PulumiYamlConfig
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class PulumiStack(PulumiYamlConfig):
    # TODO: requires documentation
    """ data class to model Pulumi stack YAML file: Pulumi.<stack name>.yaml """
    encryptionsalt: str
    config: dict = field(default_factory=dict)
    name: str = field(default_factory=utils.generate_stack_name)

    @property
    def contents(self) -> dict:
        contents = self.__dict__.copy()
        if 'name' in contents:
            contents.pop('name')  # name is not a valid field in the YAML file
        return contents

    @property
    def filepath(self) -> Path:
        return Path.cwd().joinpath(f'Pulumi.{self.name}.yaml')
