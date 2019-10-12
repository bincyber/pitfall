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

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Union
import yaml


DEFAULT_PULUMI_HOME = str(Path('~/.pulumi').expanduser())
DEFAULT_PULUMI_CONFIG_PASSPHRASE = 'pulumi'


@dataclass
class PulumiYamlConfig(ABC):
    """ abstract base class for Pulumi YAML config files """
    def __str__(self) -> str:  # pragma: no cover
        return self.to_yaml()

    def to_yaml(self) -> str:
        return yaml.dump(self.contents)

    def write(self) -> None:
        self.filepath.write_text(self.to_yaml())

    @abstractmethod
    def contents(self):  # pragma: no cover
        pass

    @abstractmethod
    def filepath(self):  # pragma: no cover
        pass

    @property
    def filename(self) -> str:
        return self.filepath.name


@dataclass
class PulumiConfigurationKey:
    # TODO: requires documentation
    name: str
    value: Union[int, float, str, bytes, bool]  # require_object() or require_secret_object() not supported at this time
    encrypted: bool = False

    def to_dict(self) -> dict:
        """ returns a dictionary representation of this object """
        key = self.name
        value = self.value

        if self.encrypted:
            value = {'secure': self.value}  # to be encrypted by _encrypt_and_format_config()

        return {key: value}
