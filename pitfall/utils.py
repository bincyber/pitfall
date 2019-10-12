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
from contextlib import contextmanager
from Cryptodome.Cipher import AES
from Cryptodome.Hash import SHA1, SHA256
from Cryptodome.Protocol.KDF import PBKDF2
from Cryptodome.Random import get_random_bytes
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Callable, Dict, Tuple
import base64
import distutils.spawn
import sys
import uuid


def get_random_string(length: int = 32) -> str:
    """
    This function returns an alphanumeric string of the requested length.

    :param int length: the length of the random string. Max of 32 characters
    :returns: a random string
    :rtype: str
    """
    if length > 32:
        length = 32
    elif length <= 0:
        length = 1
    random_string = uuid.uuid4().hex
    return random_string[:length]


def generate_project_name() -> str:
    """
    This fuction generates and returns a unique name for the Pulumi Project.

    :returns: a unique project name
    :rtype: str
    """
    random_string = get_random_string(16)
    project_name = f"pitf-project-{random_string}"
    return project_name


def generate_stack_name() -> str:
    """
    This fuction generates and returns a unique name for the Pulumi Stack
    """
    random_string = get_random_string(16)
    stack_name = f"pitf-stack-{random_string}"
    return stack_name


def get_project_backend_url(path: Path = None) -> Dict[str, str]:
    """
    This fuction returns the location of the Pulumi state directory. By default,
    the current working directory.

    :param Path path: a path object
    :returns: dictionary containing a file URL pointing to the Pulumi state directory
    :rtype: dict
    """
    if path is None:
        path = Path.cwd()
    return {"url": path.as_uri()}


def generate_aes_encryption_key(password: str, salt: bytes = None) -> Tuple[bytes, bytes]:
    """ uses PBKDF2 with SHA256 HMAC to derive a 32-byte encryption key from the provided password """
    if salt is None:
        salt = get_random_bytes(8)
    return PBKDF2(password, salt, 32, count=1000000, hmac_hash_module=SHA256), salt


def encrypt_with_aes_gcm(key: bytes, plaintext: bytes) -> Tuple[bytes, bytes, bytes]:
    """ encrypts plaintext using 256-bit AES in GCM mode """
    nonce  = get_random_bytes(12)
    cipher = AES.new(key=key, nonce=nonce, mode=AES.MODE_GCM, mac_len=16)

    ciphertext, mac = cipher.encrypt_and_digest(plaintext)
    return nonce, ciphertext, mac


def decrypt_with_aes_gcm(key: bytes, nonce: bytes, ciphertext: bytes, mac: bytes) -> bytes:
    """ decrypts 256-bit AES encrypted ciphertext """
    cipher    = AES.new(key=key, nonce=nonce, mode=AES.MODE_GCM, mac_len=16)
    plaintext = cipher.decrypt_and_verify(ciphertext, mac)
    return plaintext


def generate_encryptionsalt(password: str) -> Tuple[bytes, str]:
    """ generates the base64 encoded string for the encryptionsalt field in Pulumi stack files """
    plaintext = b'pulumi'

    key, salt               = generate_aes_encryption_key(password)
    nonce, ciphertext, mac  = encrypt_with_aes_gcm(key, plaintext)

    # 16-byte MAC tag is appended to the ciphertext
    message = ciphertext + mac

    salt_b64    = base64.b64encode(salt).decode('utf-8')
    nonce_b64   = base64.b64encode(nonce).decode('utf-8')
    message_b64 = base64.b64encode(message).decode('utf-8')

    encryptionsalt = f"v1:{salt_b64}:v1:{nonce_b64}:{message_b64}"

    return key, encryptionsalt


def get_encrypted_secret(plaintext: bytes, key: bytes) -> str:
    """ returns a base64 formatted encrypted Pulumi secret """
    nonce, ciphertext, mac  = encrypt_with_aes_gcm(key, plaintext)

    # 16-byte MAC tag is appended to the ciphertext
    message = ciphertext + mac

    nonce_b64   = base64.b64encode(nonce).decode('utf-8')
    message_b64 = base64.b64encode(message).decode('utf-8')

    encrypted_secret = f"v1:{nonce_b64}:{message_b64}"

    return encrypted_secret


def get_current_timestamp() -> str:
    """ returns the current date and time in ISO 8601 format """
    return datetime.now().astimezone().isoformat()


def sha1sum(data: bytes) -> str:
    """ returns the SHA1 hash of the provided data """
    h = SHA1.new()
    h.update(data)
    return h.hexdigest()


def sha256sum(data: bytes) -> str:
    """ returns the SHA256 hash of the provided data """
    h = SHA256.new()
    h.update(data)
    return h.hexdigest()


def decode_utf8(data: bytes) -> str:
    return data.decode('utf-8')


def get_directory_abspath(path: Path) -> Path:
    if not path.is_dir():
        path = path.parent
    return path.absolute()


def find_pulumi_binary() -> str:
    location = distutils.spawn.find_executable('pulumi')
    if location is None:
        raise exceptions.PulumiBinaryNotFoundError("Could not find the pulumi binary on the system")
    return location


@contextmanager
def capture_stdout(f: Callable, *args, **kwargs):
    """ context manager that captures whatever is output to sys.stdout """
    out        = sys.stdout
    sys.stdout = StringIO()

    try:
        f(*args, **kwargs)
        sys.stdout.seek(0)
        yield sys.stdout.read()
    finally:
        sys.stdout = out
