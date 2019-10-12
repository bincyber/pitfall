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

from dataclasses import FrozenInstanceError
from pathlib import Path
from urllib.parse import ParseResult
from pitfall.project import PulumiProject
from pitfall import utils
import os
import yaml
import unittest


class TestPulumiProject(unittest.TestCase):
    def setUp(self):
        self.pulumi_project = PulumiProject()
        self.pwd = Path.cwd()

    def tearDown(self):
        os.chdir(self.pwd)

    def test_dataclass_is_frozen(self):
        with self.assertRaises(FrozenInstanceError):
            self.pulumi_project.name = "unit-test"

    def test_class_attrs(self):
        expected = 'python'
        self.assertEqual(expected, self.pulumi_project.runtime)

        expected = utils.get_project_backend_url()
        self.assertDictEqual(expected, self.pulumi_project.backend)

        self.assertIsInstance(self.pulumi_project.url, ParseResult)

        self.assertEqual(expected["url"], self.pulumi_project.url.geturl())

        expected = 'Pulumi.yaml'
        self.assertEqual(expected, self.pulumi_project.filename)

    def test_to_yaml(self):
        yaml_contents = self.pulumi_project.to_yaml()
        self.assertIsInstance(yaml_contents, str)

        expected = yaml.safe_load(yaml_contents)
        self.assertIsInstance(expected, dict)
        self.assertDictEqual(expected, self.pulumi_project.contents)

    def test_write(self):
        os.chdir('/tmp')
        self.pulumi_project.write()

        path = Path('/tmp/Pulumi.yaml')
        self.assertTrue(path.exists())
        self.assertTrue(path.is_file())

        expected = yaml.safe_load(path.read_text())
        self.assertDictEqual(expected, self.pulumi_project.contents)
