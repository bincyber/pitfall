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

from pitfall.config import PulumiConfigurationKey
import unittest


class TestPulumiConfigKey(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_plaintext_config_key(self):
        k = v = 'test'

        cfg_variable = PulumiConfigurationKey(name=k, value=v)

        cfg_variable_dict = cfg_variable.to_dict()
        self.assertIsInstance(cfg_variable_dict, dict)
        self.assertDictEqual(cfg_variable_dict, {k: v})

    def test_encrypted_config_key(self):
        k = 'dbpassword'
        v = b'asdfghjkl'

        cfg_variable = PulumiConfigurationKey(name=k, value=v, encrypted=True)

        cfg_variable_dict = cfg_variable.to_dict()
        self.assertIsInstance(cfg_variable_dict, dict)
        self.assertDictEqual(cfg_variable_dict, {k: {'secure': v}})
        self.assertEqual(v, cfg_variable_dict[k].get('secure'))
