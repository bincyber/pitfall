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


class PulumiBinaryNotFoundError(Exception):
    """ raised when the pulumi binary cannot be found on the system """
    def __init__(self, message='Could not find the pulumi binary on the system'):
        super().__init__(message)


class PulumiVersionExecError(Exception):
    """ raised when `pulumi version` returns non-zero exit code """


class PulumiPluginInstallError(Exception):
    """ raised when pulumi fails to install a plugin """


class PulumiStackOutputError(Exception):
    """ raised when pulumi fails to return stack outputs """


class PulumiPreviewExecError(Exception):
    """ raised when `pulumi preview` returns non-zero exit code """


class PulumiUpExecError(Exception):
    """ raised when `pulumi up` returns non-zero exit code """


class PulumiDestroyExecError(Exception):
    """ raised when `pulumi destroy` returns non-zero exit code """
