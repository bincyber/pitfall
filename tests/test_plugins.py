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

from pitfall.plugins import PulumiPlugin
import unittest


class TestPulumiPlugin(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_class_attrs(self):
        kind    = 'resource'
        name    = 'aws'
        version = '0.0.1'

        plugin = PulumiPlugin(kind=kind, name=name, version=version)

        self.assertEqual(kind, plugin.kind)
        self.assertEqual(name, plugin.name)
        self.assertEqual(version, plugin.version)
