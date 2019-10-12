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
from pitfall.state import PulumiState, PulumiResource
from pitfall import utils
from pitfall import exceptions
from unittest.mock import patch, MagicMock
import copy
import os
import json
import shutil
import subprocess
import unittest


class TestPulumiState(unittest.TestCase):
    def setUp(self):
        _, encryptionsalt = utils.generate_encryptionsalt('test')

        self.pulumi_state = PulumiState(
            stack='unit-test',
            encryptionsalt=encryptionsalt
        )

        self.pwd = Path.cwd()
        os.chdir('/tmp')

    def tearDown(self):
        os.chdir(self.pwd)
        path = Path('/tmp/.pulumi')
        shutil.rmtree(path, ignore_errors=True)

    def test_class_attrs(self):
        expected = 'unit-test'
        self.assertEqual(expected, self.pulumi_state.stack)

        self.assertIsInstance(self.pulumi_state.encryptionsalt, str)

        self.assertIsInstance(self.pulumi_state.new, dict)
        for key in ['version', 'checkpoint']:
            self.assertIn(key, self.pulumi_state.new)
        self.assertEqual(3, self.pulumi_state.new['version'])
        self.assertEqual('unit-test', self.pulumi_state.new['checkpoint']['stack'])

        expected = Path.cwd().joinpath('.pulumi')
        self.assertEqual(expected, self.pulumi_state.dirpath)
        self.assertIsInstance(self.pulumi_state.dirpath, Path)

        expected = Path.cwd().joinpath('.pulumi/stacks/unit-test.json')
        self.assertEqual(expected, self.pulumi_state.filepath)
        self.assertIsInstance(self.pulumi_state.filepath, Path)

        expected = 3
        self.assertEqual(expected, self.pulumi_state.version)
        self.assertIsInstance(self.pulumi_state.version, int)

    def test_pulumi_version(self):
        stdout = b'v1.3.3\n'

        completed_process = subprocess.CompletedProcess(args=['pulumi', 'version'], returncode=0, stdout=stdout, stderr=None)

        with patch('subprocess.run', MagicMock(return_value=completed_process)):
            expected = 'v1.3.3'
            actual   = self.pulumi_state.pulumi_version
            self.assertEqual(expected, actual)

    def test_pulumi_version_raises_exception(self):
        stderr = b'some error was encountered'

        completed_process = subprocess.CompletedProcess(args=['pulumi', 'version'], returncode=255, stdout=b'', stderr=stderr)

        with patch('subprocess.run', MagicMock(return_value=completed_process)):
            try:
                self.pulumi_state.pulumi_version
            except exceptions.PulumiVersionExecError as e:
                err = e.args[0]

            self.assertIsInstance(err, str)
            self.assertEqual(err, stderr.decode('utf-8'))

    def test_magic_cookie(self):
        stdout = b'v1.3.3\n'

        completed_process = subprocess.CompletedProcess(args=['pulumi', 'version'], returncode=0, stdout=stdout, stderr=None)

        with patch('subprocess.run', MagicMock(return_value=completed_process)):
            expected = 'd5876dc5dbcc5e01f522044c21c1c24de43ad1179e8d38a473039122ec42665a'
            actual   = self.pulumi_state.magic_cookie
            self.assertEqual(expected, actual)

    def test_no_current_state(self):
        self.assertDictEqual(self.pulumi_state.new, self.pulumi_state.current)

    def test_current_state(self):
        expected = {"version": 3, "checkpoint": {"stack": self.pulumi_state.stack, "resources": []}}
        self.pulumi_state.filepath.parent.mkdir(parents=True, exist_ok=False)
        self.pulumi_state.filepath.write_text(json.dumps(expected))
        self.assertDictEqual(expected, self.pulumi_state.current)

    def test_no_previous_state(self):
        self.assertDictEqual(self.pulumi_state.new, self.pulumi_state.previous)

    def test_previous_state(self):
        backups_directory = self.pulumi_state.dirpath.joinpath(f'backups/{self.pulumi_state.stack}')
        backups_directory.mkdir(parents=True, exist_ok=True)

        oldest_state_file   = backups_directory.joinpath(f'{self.pulumi_state.stack}.1568899856000000000.json')
        older_state_file    = backups_directory.joinpath(f'{self.pulumi_state.stack}.1568989822000000000.json')
        previous_state_file = backups_directory.joinpath(f'{self.pulumi_state.stack}.1569080793000000000.json')
        current_state_file  = backups_directory.joinpath(f'{self.pulumi_state.stack}.1569168944000000000.json')

        oldest_state_file.touch()
        older_state_file.touch()

        previous_state_file.write_text(json.dumps(self.pulumi_state.new, indent=4))

        current_state = copy.deepcopy(self.pulumi_state.new)
        current_state["checkpoint"]["latest"]["manifest"]["time"] = utils.get_current_timestamp()
        current_state["checkpoint"]["latest"]["resources"] = []

        current_state_file.write_text(json.dumps(current_state, indent=4))

        self.maxDiff = None
        expected     = self.pulumi_state.new
        actual       = self.pulumi_state.previous
        self.assertDictEqual(expected, actual)

    def test_to_json(self):
        expected = json.dumps(self.pulumi_state.new, indent=4)
        self.assertEqual(expected, self.pulumi_state.to_json())

    def test_write(self):
        self.assertFalse(self.pulumi_state.filepath.exists())
        self.pulumi_state.write()
        self.assertTrue(self.pulumi_state.filepath.exists())

        expected = json.dumps(self.pulumi_state.new, indent=4)
        self.assertEqual(expected, self.pulumi_state.to_json())

    def test_resources(self):
        # copy the test state file to the temp Pulumi state directory
        test_state = Path(__file__).parent.joinpath('test_data/state.json').read_text()
        self.pulumi_state.filepath.parent.mkdir(parents=True, exist_ok=False)
        self.pulumi_state.filepath.write_text(test_state)

        resources = self.pulumi_state.resources
        self.assertEqual(1, len(resources))

        resource = resources[0]
        self.assertIsInstance(resource, PulumiResource)
        self.assertEqual("pitfall-test-bucket-7915523", resource.id)
        self.assertEqual("aws:s3/bucket:Bucket", resource.type)
        self.assertIsInstance(resource.parent, str)
        self.assertIsInstance(resource.provider, str)
        self.assertIsInstance(resource.inputs, dict)
        self.assertIsInstance(resource.outputs, dict)
        self.assertIsInstance(resource.dependencies, dict)
