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
from pitfall.stack import PulumiStack
from pitfall import utils
import os
import unittest
import yaml


class TestPulumiStack(unittest.TestCase):
    def setUp(self):
        _, encryptionsalt = utils.generate_encryptionsalt('test')

        self.pulumi_stack = PulumiStack(
            name="unit-test",
            encryptionsalt=encryptionsalt,
            config={
                "aws:region": "us-west-1",
                "env": "test"
            }
        )

        self.pwd = Path.cwd()

    def tearDown(self):
        os.chdir(self.pwd)

    def test_class_attrs(self):
        expected = 'unit-test'
        self.assertEqual(expected, self.pulumi_stack.name)

        self.assertTrue(self.pulumi_stack.encryptionsalt.startswith('v1:'))
        self.assertEqual(5, len(self.pulumi_stack.encryptionsalt.split(':')))

        expected = 'Pulumi.unit-test.yaml'
        self.assertEqual(expected, self.pulumi_stack.filename)

    def test_to_yaml(self):
        yaml_contents = self.pulumi_stack.to_yaml()
        self.assertIsInstance(yaml_contents, str)

        expected = yaml.safe_load(yaml_contents)
        self.assertIsInstance(expected, dict)
        self.assertDictEqual(expected, self.pulumi_stack.contents)

    def test_write(self):
        os.chdir('/tmp')
        self.pulumi_stack.write()

        path = Path('/tmp/Pulumi.unit-test.yaml')
        self.assertTrue(path.exists())
        self.assertTrue(path.is_file())

        contents = yaml.safe_load(path.read_text())
        self.assertDictEqual(contents, self.pulumi_stack.contents)
