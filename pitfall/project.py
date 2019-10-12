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
from urllib.parse import urlparse, ParseResult


@dataclass(frozen=True)
class PulumiProject(PulumiYamlConfig):
    # TODO: requires documentation
    """ data class to model Pulumi project YAML file: Pulumi.yaml """
    name: str = field(default_factory=utils.generate_project_name)
    description: str = "Pulumi Python program"
    runtime: str = "python"
    backend: dict = field(default_factory=utils.get_project_backend_url)

    @property
    def contents(self) -> dict:
        return self.__dict__

    @property
    def filepath(self) -> Path:
        return Path.cwd().joinpath('Pulumi.yaml')

    @property
    def url(self) -> ParseResult:
        return urlparse(self.backend.get("url", None))
