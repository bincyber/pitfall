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


from . import exceptions
from . import utils
from .config import PulumiConfigurationKey, DEFAULT_PULUMI_CONFIG_PASSPHRASE, DEFAULT_PULUMI_HOME
from .actions import PulumiPreview, PulumiUp, PulumiDestroy
from .project import PulumiProject
from .plugins import PulumiPlugin
from .stack import PulumiStack
from .state import PulumiState
from dataclasses import dataclass
from distutils import dir_util
from pathlib import Path
from typing import Dict, List, Union, Any
import json
import os
import shutil
import subprocess
import tempfile


@dataclass
class PulumiIntegrationTestOptions:
    # TODO: requires documentation
    cleanup: bool = False
    destroy: bool = False
    preview: bool = True
    up:      bool = False  # noqa: E241
    verbose: bool = False


class PulumiIntegrationTest:
    """ class for use with Pulumi integration tests """
    # TODO: requires documentation
    def __init__(
            self,
            directory: Union[str, Path] = Path.cwd(),
            config: List[PulumiConfigurationKey] = None,
            plugins: List[PulumiPlugin] = None,
            opts: PulumiIntegrationTestOptions = PulumiIntegrationTestOptions()
    ) -> None:

        self.config = config
        if self.config is None:
            self.config = []

        self.plugins = plugins
        if self.plugins is None:
            self.plugins = []

        self.opts = opts

        self.code_directory = utils.get_directory_abspath(directory)
        self.old_directory  = Path.cwd()
        self.tmp_directory  = self._generate_test_directory()

        self._set_pulumi_envvars()

        backend = utils.get_project_backend_url(path=self.tmp_directory)  # this places the pulumi state directory in the test directory

        self.encryption_key, self.encryptionsalt = utils.generate_encryptionsalt(self.pulumi_config_passphrase)

        self.project = PulumiProject(backend=backend)
        self.stack   = PulumiStack(encryptionsalt=self.encryptionsalt, config=self._encrypt_and_format_config())
        self.state   = PulumiState(stack=self.stack.name, encryptionsalt=self.encryptionsalt)

        self.preview = PulumiPreview(verbose=self.opts.verbose)
        self.up      = PulumiUp(verbose=self.opts.verbose)
        self.destroy = PulumiDestroy(verbose=self.opts.verbose)

    def __enter__(self):
        self.setup()

        if self.opts.preview:
            self.preview.execute()

        if self.opts.up:
            self.up.execute()

        return self

    def __exit__(self, exc_type, exc_value, exc_traceback) -> None:
        self.delete()
        self._change_directory('old')  # return to the starting directory

    def setup(self) -> None:
        """ prepares the Pulumi integration test environment """
        self._copy_pulumi_code()  # copy Pulumi code directory to temp directory
        self._change_directory('test')  # change to the temp directory
        self.project.write()  # create the Pulumi project YAML file
        self.stack.write()  # create the Pulumi stack YAML file
        self.state.write()  # initialize Pulumi state
        self._select_current_stack()  # set the current stack as active
        self._install_pulumi_plugins()  # install plugins

    def delete(self) -> None:
        """ deletes the workspace and temporary test directories """
        if self.opts.destroy:
            self.destroy.execute()

        if self.opts.cleanup:
            shutil.rmtree(self.tmp_directory, ignore_errors=True)
            try:
                self.workspace.unlink()
            except FileNotFoundError:
                pass

    def _encrypt_and_format_config(self) -> dict:
        pulumi_stack_config: Dict[str, Any] = {}

        for i in self.config:
            name  = i.name
            value = i.value

            if name.find(':') == -1:
                name = f'{self.project.name}:{i.name}'

            if i.encrypted:
                ciphertext  = utils.get_encrypted_secret(plaintext=i.value, key=self.encryption_key)
                value       = {'secure': ciphertext}

            pulumi_stack_config.update({name: value})

        return pulumi_stack_config

    def _install_pulumi_plugins(self) -> None:
        for plugin in self.plugins:
            cmd = [self.pulumi_binary, 'plugin', 'install', plugin.kind, plugin.name, plugin.version]
            p   = subprocess.run(cmd, capture_output=True)

            if p.returncode != 0:
                err = f"Failed to install plugin: {plugin.kind} {plugin.name} {plugin.version}. {p.stderr}"
                raise exceptions.PulumiPluginInstallError(err)

            if self.opts.verbose:
                print(f"Installed plugin: {plugin.kind} {plugin.name} {plugin.version}")

    def _generate_test_directory(self) -> Path:
        """ creates a temporary test directory in the current working directory """
        return Path(tempfile.mkdtemp(prefix="pitf-", dir=Path.cwd()))

    def _change_directory(self, choice: str) -> None:
        """ changes to the test or old directory specified by choice"""
        if choice == 'test':
            path = self.tmp_directory
        elif choice == 'old':
            path = self.old_directory

        try:
            os.chdir(path)
        except Exception:
            os.chdir(self.old_directory)
            print(f"Error: Failed to change directory to {choice} directory: {path}")
            raise

    def _copy_pulumi_code(self) -> list:
        """ copies the contents of the pulumi code directory to the test directory """
        src = str(self.code_directory)
        dst = str(self.tmp_directory)
        return dir_util.copy_tree(src, dst)

    def _set_pulumi_envvars(self) -> None:
        # the user's environment variables take precedence over pitfall defaults
        pulumi_home              = os.environ.get('PULUMI_HOME', DEFAULT_PULUMI_HOME)
        pulumi_config_passphrase = os.environ.get('PULUMI_CONFIG_PASSPHRASE', DEFAULT_PULUMI_CONFIG_PASSPHRASE)

        self.pulumi_environment_variables = {
            'PULUMI_HOME': pulumi_home,
            'PULUMI_CONFIG_PASSPHRASE': pulumi_config_passphrase,
            'PULUMI_RETAIN_CHECKPOINTS': 'true',
            'PULUMI_SKIP_UPDATE': 'true'
        }

        for key, value in self.pulumi_environment_variables.items():
            os.environ[key] = value

        # unset this environment variable to ensure state files are copied to <pulumi_home>/backups
        envvar = 'PULUMI_DISABLE_CHECKPOINT_BACKUPS'
        if envvar in os.environ:
            os.environ.pop(envvar)

    def _select_current_stack(self) -> None:
        """ selects the current stack by creating the workspace file for it """
        contents = {"stack": self.stack.name}

        self.workspace.parent.mkdir(parents=True, exist_ok=True)
        self.workspace.write_text(json.dumps(contents))

    def get_stack_outputs(self) -> dict:
        """ returns a dictionary of the stack's output properties """
        cmd = [self.pulumi_binary, 'stack', 'output', '--json', '--non-interactive']

        process = subprocess.run(cmd, capture_output=True)

        stdout = utils.decode_utf8(process.stdout)

        if process.returncode != 0:
            raise exceptions.PulumiStackOutputError(stdout)

        return json.loads(stdout)

    @property
    def pulumi_binary(self) -> str:
        return utils.find_pulumi_binary()

    @property
    def pulumi_home(self) -> str:
        return self.pulumi_environment_variables['PULUMI_HOME']

    @property
    def pulumi_config_passphrase(self) -> str:
        return self.pulumi_environment_variables['PULUMI_CONFIG_PASSPHRASE']

    @property
    def workspace(self) -> Path:
        workspace_directory  = Path(self.pulumi_home).expanduser().joinpath('workspaces')
        project_path_sha1sum = utils.sha1sum(bytes(self.project.filepath))  # the SHA1 sum of the absolute path of the Pulumi.yaml file
        workspace_filename   = f'{self.project.name}-{project_path_sha1sum}-workspace.json'
        return workspace_directory.joinpath(workspace_filename)
