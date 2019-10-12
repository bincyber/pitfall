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
from pitfall import utils
from pitfall import exceptions
from pitfall.config import DEFAULT_PULUMI_CONFIG_PASSPHRASE
from unittest.mock import patch, MagicMock
import base64
import tempfile
import unittest


class TestUtils(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_get_random_string(self):
        string = utils.get_random_string(16)
        self.assertEqual(16, len(string))

        string = utils.get_random_string(33)
        self.assertEqual(32, len(string))

        string = utils.get_random_string(-1)
        self.assertEqual(1, len(string))

    def test_generate_project_name(self):
        ret = utils.generate_project_name()

        # ensure stack names always being with 'pitf-project'
        self.assertTrue(ret.startswith('pitf-project-'))

        splitted = ret.split('-')
        self.assertEquals(3, len(splitted))
        self.assertEqual(16, len(splitted[-1]))

        # ensure randomness of stack name
        ret2 = utils.generate_project_name()
        self.assertNotEqual(ret, ret2)

    def test_generate_stack_name(self):
        ret = utils.generate_stack_name()

        # ensure stack names always being with 'pitf-stack'
        self.assertTrue(ret.startswith('pitf-stack-'))

        splitted = ret.split('-')
        self.assertEquals(3, len(splitted))
        self.assertEqual(16, len(splitted[-1]))

        # ensure randomness of stack name
        ret2 = utils.generate_stack_name()
        self.assertNotEqual(ret, ret2)

    def test_get_project_backend_url(self):
        expected = {"url": Path.cwd().as_uri()}
        actual   = utils.get_project_backend_url()

        self.assertEqual(expected, actual)

        path = Path('/tmp')
        expected = {"url": path.as_uri()}
        actual   = utils.get_project_backend_url(path)

        self.assertEqual(expected, actual)

    def test_generate_aes_encryption_key(self):
        password = 'password'

        key, salt = utils.generate_aes_encryption_key(password)

        self.assertEqual(32, len(key))
        self.assertEqual(8, len(salt))

        self.assertIsInstance(key, bytes)
        self.assertIsInstance(salt, bytes)

    def test_encrypt_decrypt_with_aes_gcm(self):
        password = 'supersecurepassword'
        plaintext = b'pulumi'

        key, _ = utils.generate_aes_encryption_key(password)

        nonce, ciphertext, mac = utils.encrypt_with_aes_gcm(key, plaintext)

        self.assertEqual(12, len(nonce))

        self.assertEqual(bytes, type(nonce))
        self.assertEqual(bytes, type(ciphertext))
        self.assertEqual(bytes, type(mac))

        decrypted = utils.decrypt_with_aes_gcm(key, nonce, ciphertext, mac)

        self.assertEqual(decrypted, plaintext)

    def test_generate_encryptionsalt(self):
        _, encryptionsalt = utils.generate_encryptionsalt(DEFAULT_PULUMI_CONFIG_PASSPHRASE)

        version, salt_b64, _, nonce_b64, ciphertext_b64 = encryptionsalt.split(':')
        self.assertEqual('v1', version)

        salt = base64.b64decode(salt_b64)
        self.assertIsInstance(salt, bytes)
        self.assertEqual(8, len(salt))

        nonce = base64.b64decode(nonce_b64)
        self.assertIsInstance(nonce, bytes)
        self.assertEqual(12, len(nonce))

        ciphertext = base64.b64decode(salt_b64)
        self.assertIsInstance(ciphertext, bytes)

    def test_verify_encryptionsalt(self):
        encryptionsalt = 'v1:fKW0HhgPPt8=:v1:jGE7R0+7qd3jUOlx:9IkhVrRrOgMRgrPnr9xbKJCUR0IV8Q=='
        _, salt_b64, _, nonce_b64, message_b64 = encryptionsalt.split(':')

        salt = base64.b64decode(salt_b64)
        self.assertIsInstance(salt, bytes)
        self.assertEqual(8, len(salt))

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

        self.assertEqual(len('pulumi'), len(ciphertext))
        self.assertEqual(16, len(mac))

        key, _ = utils.generate_aes_encryption_key(password=DEFAULT_PULUMI_CONFIG_PASSPHRASE, salt=salt)
        self.assertEqual(32, len(key))

        expected = b'pulumi'
        actual   = utils.decrypt_with_aes_gcm(key=key, nonce=nonce, ciphertext=ciphertext, mac=mac)
        self.assertEqual(expected, actual)

    def test_get_encrypted_secret(self):
        plaintext = b'thisvalueistopsecret'

        password = 'supersecurepassword'

        key, _ = utils.generate_aes_encryption_key(password)

        encrypted_secret = utils.get_encrypted_secret(plaintext, key)

        version, nonce_b64, message_b64 = encrypted_secret.split(':')

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

        self.assertEqual(len(plaintext), len(ciphertext))
        self.assertEqual(16, len(mac))

        decrypted = utils.decrypt_with_aes_gcm(key=key, nonce=nonce, ciphertext=ciphertext, mac=mac)
        self.assertEqual(plaintext, decrypted)

    def test_sha1sum(self):
        message = b'hello world'

        expected = '2aae6c35c94fcfb415dbe95f408b9ce91ee846ed'
        actual   = utils.sha1sum(message)
        self.assertEqual(expected, actual)
        self.assertIsInstance(actual, str)

    def test_sha256sum(self):
        message = b'hello world'

        expected = 'b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9'
        actual   = utils.sha256sum(message)
        self.assertEqual(expected, actual)
        self.assertIsInstance(actual, str)

    def test_decode_utf8(self):
        expected = 'hello world'
        actual   = utils.decode_utf8(b'hello world')
        self.assertEqual(expected, actual)

    def test_get_directory_abspath(self):
        with tempfile.TemporaryDirectory(prefix='pitf-', dir='/tmp') as d:
            dir_abspath = utils.get_directory_abspath(Path(d))
            self.assertTrue(dir_abspath.is_dir())
            self.assertTrue(dir_abspath.is_absolute())

            file_path = dir_abspath.joinpath('test.txt')
            file_path.touch()

            file_parent_abspath = utils.get_directory_abspath(file_path)
            self.assertTrue(file_parent_abspath.is_dir())
            self.assertTrue(file_parent_abspath.is_absolute())
            self.assertEqual(dir_abspath, file_parent_abspath)

    def test_find_pulumi_binary(self):
        with patch('distutils.spawn.find_executable', MagicMock(return_value='/usr/local/bin/pulumi')):
            expected = '/usr/local/bin/pulumi'
            actual = utils.find_pulumi_binary()
            self.assertEqual(expected, actual)

    def test_find_pulumi_binary_raises_exception(self):
        with patch('distutils.spawn.find_executable', MagicMock(return_value=None)):
            with self.assertRaises(exceptions.PulumiBinaryNotFoundError):
                self.assertIsNone(utils.find_pulumi_binary())
