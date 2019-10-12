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

from pathlib import Path
from pitfall.core import PulumiIntegrationTest, PulumiIntegrationTestOptions
from pitfall.config import PulumiConfigurationKey, DEFAULT_PULUMI_CONFIG_PASSPHRASE, DEFAULT_PULUMI_HOME
from pitfall.plugins import PulumiPlugin
from pitfall import exceptions
from pitfall import utils
from unittest.mock import patch, MagicMock
import base64
import json
import os
import shutil
import subprocess
import tempfile
import unittest


class TestPulumiIntegrationTest(unittest.TestCase):
    def setUp(self):
        opts = PulumiIntegrationTestOptions(verbose=False, cleanup=True, preview=False)
        self.integration_test = PulumiIntegrationTest(opts=opts)

    def tearDown(self):
        self.integration_test.delete()
        self.integration_test._change_directory(choice='old')  # return to parent directory to not cause other tests to fail

        # unset environment variables
        for i in ['PULUMI_HOME', 'PULUMI_CONFIG_PASSPHRASE']:
            if i in os.environ:
                os.environ.pop(i)

    def test_encrypt_and_format_config(self):
        secret_config_key = 'dbpassword'
        secret_config_value = b'qwertyuiop'

        cfg = [
            PulumiConfigurationKey(name='aws:region', value='us-east-1'),
            PulumiConfigurationKey(name='environment', value='testing'),
            PulumiConfigurationKey(name=secret_config_key, value=secret_config_value, encrypted=True)
        ]

        self.integration_test.config = cfg

        formatted_cfg = self.integration_test._encrypt_and_format_config()

        namespace = self.integration_test.project.name

        encrypted_secret_config_value = formatted_cfg[f'{namespace}:{secret_config_key}']['secure']

        expected = {
            'aws:region': 'us-east-1',
            f'{namespace}:environment': 'testing',
            f'{namespace}:{secret_config_key}': {
                'secure': encrypted_secret_config_value
            }
        }
        self.assertDictEqual(expected, formatted_cfg)

        version, nonce_b64, message_b64 = encrypted_secret_config_value.split(':')
        self.assertEqual('v1', version)

        nonce = base64.b64decode(nonce_b64)
        self.assertIsInstance(nonce, bytes)
        self.assertEqual(12, len(nonce))

        # extract the ciphertext and MAC tag from the message
        message = base64.b64decode(message_b64)

        index = len(message) - 16  # MAC tag is 16 bytes

        ciphertext  = message[:index]  # first n bytes is the ciphertext
        mac         = message[index:]  # last 16 bytes is the MAC tag

        self.assertIsInstance(ciphertext, bytes)
        self.assertIsInstance(mac, bytes)

        self.assertEqual(len(secret_config_value), len(ciphertext))
        self.assertEqual(16, len(mac))

        decrypted = utils.decrypt_with_aes_gcm(key=self.integration_test.encryption_key, nonce=nonce, ciphertext=ciphertext, mac=mac)
        self.assertEqual(secret_config_value, decrypted)

    def test_install_pulumi_plugins_success(self):
        self.integration_test.opts.verbose = True

        # use a fixed directory to prevent redownloading plugins on each test run
        pulumi_home = Path('/tmp/.pulumi')
        pulumi_home.mkdir(exist_ok=True)

        os.environ['PULUMI_HOME'] = str(pulumi_home)

        kind    = 'resource'
        name    = 'random'
        version = 'v1.1.0'

        plugins = [
            PulumiPlugin(kind=kind, name=name, version=version)
        ]

        self.integration_test.plugins = plugins

        with utils.capture_stdout(self.integration_test._install_pulumi_plugins) as output:
            self.assertTrue(output.startswith('Installed plugin:'))

        path = Path(f'{pulumi_home}/plugins/{kind}-{name}-{version}')

        self.assertTrue(path.exists())
        self.assertTrue(path.is_dir())

    def test_install_pulumi_plugins_failure(self):
        # use a fixed directory to prevent redownloading plugins on each test run
        pulumi_home = Path('/tmp/.pulumi')
        pulumi_home.mkdir(exist_ok=True)

        os.environ['PULUMI_HOME'] = str(pulumi_home)

        kind    = 'resource'
        name    = 'invalid'
        version = 'v1.0.0'

        plugins = [
            PulumiPlugin(kind=kind, name=name, version=version)
        ]

        self.integration_test.plugins = plugins

        with self.assertRaises(exceptions.PulumiPluginInstallError):
            self.integration_test._install_pulumi_plugins()

        path = Path(f'{pulumi_home}/plugins/{kind}-{name}-{version}')
        self.assertFalse(path.expanduser().exists())

    def test_tmp_directory_name(self):
        self.assertTrue(self.integration_test.tmp_directory.name.startswith("pitf-"))

    def test_change_directory_to_old_dir(self):
        self.integration_test._change_directory(choice='old')
        self.assertEqual(Path.cwd(), self.integration_test.old_directory)

    def test_change_directory_to_test_dir(self):
        self.integration_test._change_directory(choice='test')
        self.assertEqual(Path.cwd(), self.integration_test.tmp_directory)

    def test_change_directory_raises_exception(self):
        self.integration_test.tmp_directory = Path('/tmp/does-not-exist')

        with self.assertRaises(FileNotFoundError):
            self.integration_test._change_directory(choice='test')

        self.assertEqual(Path.cwd(), self.integration_test.old_directory)

    def test_pulumi_project_backend(self):
        expected = utils.get_project_backend_url(path=self.integration_test.tmp_directory)
        self.assertDictEqual(expected, self.integration_test.project.backend)
        self.assertEqual(expected["url"], self.integration_test.project.url.geturl())

    def test_copy_pulumi_code(self):
        with tempfile.TemporaryDirectory(prefix='pitf-', dir='/tmp') as d:
            self.integration_test.code_directory = d

            pulumi_filename = '__main__.py'

            # create a dummy Pulumi Python program in the temp directory
            tmp_directory = Path(d)
            src_f1 = tmp_directory.joinpath(pulumi_filename)
            src_f1.touch()

            # create a subdirectory within the tmp directory with a dummy file
            subdir = tmp_directory.joinpath('misc')
            subdir.mkdir()
            src_f2 = subdir.joinpath('userdata.txt')
            src_f2.touch()

            self.integration_test._copy_pulumi_code()

            # verify contents were copied
            dst_f1 = self.integration_test.tmp_directory.joinpath(pulumi_filename)
            self.assertTrue(dst_f1.exists())
            self.assertTrue(dst_f1.is_file())

            dst_f2 = self.integration_test.tmp_directory.joinpath('misc/userdata.txt')
            self.assertTrue(dst_f2.exists())
            self.assertTrue(dst_f2.is_file())

    def test_set_pulumi_envvars_to_defaults(self):
        self.integration_test._set_pulumi_envvars()

        expected = os.environ.get('PULUMI_HOME')
        self.assertEqual(expected, DEFAULT_PULUMI_HOME)

        expected = os.environ.get('PULUMI_CONFIG_PASSPHRASE')
        self.assertEqual(expected, DEFAULT_PULUMI_CONFIG_PASSPHRASE)

    def test_set_pulumi_envvars_to_user_specified(self):
        pulumi_home = '/tmp'
        os.environ['PULUMI_HOME'] = pulumi_home

        pulumi_config_passphrase = 'testtest'
        os.environ['PULUMI_CONFIG_PASSPHRASE'] = pulumi_config_passphrase

        self.integration_test._set_pulumi_envvars()

        expected = os.environ.get('PULUMI_HOME')
        self.assertEqual(expected, pulumi_home)

        expected = os.environ.get('PULUMI_CONFIG_PASSPHRASE')
        self.assertEqual(expected, pulumi_config_passphrase)

    def test_set_pulumi_envvars_verify_unset_envvars(self):
        environment_variable = 'PULUMI_DISABLE_CHECKPOINT_BACKUPS'

        os.environ[environment_variable] = 'true'

        self.integration_test._set_pulumi_envvars()

        self.assertIsNone(os.environ.get(environment_variable))

    def test_workspace(self):
        self.assertTrue(self.integration_test.workspace.name.startswith(self.integration_test.project.name))
        self.assertTrue(self.integration_test.workspace.name.endswith('workspace.json'))

        parts = self.integration_test.workspace.name.split('-')
        expected = parts[-2]
        actual = utils.sha1sum(bytes(self.integration_test.project.filepath))
        self.assertEqual(expected, actual)

    def test_select_current_stack(self):
        self.integration_test._select_current_stack()
        self.assertTrue(self.integration_test.workspace.exists())
        self.assertTrue(self.integration_test.workspace.is_file())

        contents = json.loads(self.integration_test.workspace.read_text())
        self.assertEqual(self.integration_test.stack.name, contents['stack'])

    # TODO: add more tests here to verify setup works correctly end-to-end
    # perhaps use mock to verify each method as been called at most once
    def test_setup(self):
        self.integration_test.setup()

    def test_get_stack_outputs(self):
        stdout = b'{"s3_bucket_name":"pitfall-test-bucket"}'
        json_stdout = json.loads(stdout)

        completed_process = subprocess.CompletedProcess(args=['pulumi', 'stack', 'output', '--json'], returncode=0, stdout=stdout, stderr=b'')

        with patch('subprocess.run', MagicMock(return_value=completed_process)):
            outputs = self.integration_test.get_stack_outputs()

            self.assertIsInstance(outputs, dict)
            self.assertDictEqual(json_stdout, outputs)

    def test_get_stack_outputs_raises_exception(self):
        stdout = b'error: no Pulumi.yaml project file found'

        completed_process = subprocess.CompletedProcess(args=['pulumi', 'stack', 'output', '--json'], returncode=255, stdout=stdout, stderr=b'')

        err = None
        with patch('subprocess.run', MagicMock(return_value=completed_process)):
            try:
                self.integration_test.get_stack_outputs()
            except exceptions.PulumiStackOutputError as e:
                err = e.args[0]

        self.assertIsInstance(err, str)

        expected = "error: no Pulumi.yaml project file found"
        self.assertEqual(expected, err)


class TestPulumiIntegrationTestWithContextManager(unittest.TestCase):
    def setUp(self):
        self.pwd = Path.cwd()

    def tearDown(self):
        os.chdir(self.pwd)

        # unset environment variables
        for i in ['PULUMI_HOME', 'PULUMI_CONFIG_PASSPHRASE']:
            if i in os.environ:
                os.environ.pop(i)

    def test_context_manager_no_cleanup(self):
        tmp_directory = None

        opts = PulumiIntegrationTestOptions(cleanup=False, preview=False)

        with PulumiIntegrationTest(opts=opts) as t:
            self.assertIsInstance(t, PulumiIntegrationTest)
            self.assertTrue(t.tmp_directory.name.startswith("pitf-"))

            tmp_directory = t.tmp_directory

        self.assertTrue(tmp_directory.exists())
        shutil.rmtree(tmp_directory)

    def test_context_manager_with_cleanup(self):
        tmp_directory = None

        opts = PulumiIntegrationTestOptions(cleanup=True, preview=False)

        with PulumiIntegrationTest(opts=opts) as t:
            self.assertIsInstance(t, PulumiIntegrationTest)
            self.assertTrue(t.tmp_directory.name.startswith("pitf-"))

            tmp_directory = t.tmp_directory

        self.assertFalse(tmp_directory.exists())

    def test_context_manager_auto_preview(self):
        opts = PulumiIntegrationTestOptions(cleanup=True, preview=True, up=False, destroy=False)

        with patch('pitfall.core.PulumiPreview', autospec=True) as mock_preview:
            mock_preview.return_value.execute.return_value = True

            with PulumiIntegrationTest(opts=opts) as t:
                self.assertIsInstance(t, PulumiIntegrationTest)

            mock_preview.return_value.execute.assert_called()

    def test_context_manager_auto_up(self):
        opts = PulumiIntegrationTestOptions(cleanup=True, preview=False, up=True, destroy=False)

        with patch('pitfall.core.PulumiUp', autospec=True) as mock_up:
            mock_up.return_value.execute.return_value = True

            with PulumiIntegrationTest(opts=opts) as t:
                self.assertIsInstance(t, PulumiIntegrationTest)

            mock_up.return_value.execute.assert_called()

    def test_context_manager_auto_delete(self):
        opts = PulumiIntegrationTestOptions(cleanup=True, preview=False, up=False, destroy=True)

        with patch('pitfall.core.PulumiDestroy', autospec=True) as mock_destroy:
            mock_destroy.return_value.execute.return_value = True

            with PulumiIntegrationTest(opts=opts) as t:
                self.assertIsInstance(t, PulumiIntegrationTest)

            mock_destroy.return_value.execute.assert_called()
