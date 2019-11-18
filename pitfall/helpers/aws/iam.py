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

from pitfall.utils import get_random_string
from typing import List
import boto3
import time


class TemporaryUser:
    """
    Generates a temporary IAM user. Attaches Managed IAM policies
    to this user and generates an Access Key and Secret Key.

    Supports a context manager to automatically create and delete this temporary user.

    :type policies: list
    :param policies: A list of IAM Policy ARNs to attach to this user.

    :type iam_client: botocore.session.Session
    :param iam_client: A boto3 IAM service client to use instead of creating a new default one.

    :type wait: bool
    :param wait: If set to True, the context manager waits 10 seconds for the Access Key and Secret Key to become active.
    """
    def __init__(self, policies: List[str], iam_client=None, wait=True):
        self.iam_policies = policies
        self.iam_client   = boto3.client('iam') if iam_client is None else iam_client
        self.wait         = wait

        self.username = self.__generate_username()

    def __repr__(self) -> str:  # pragma: no cover
        return "TemporaryIAMUser(policies=%r, iam_client=%r)" % (self.iam_policies, self.iam_client)

    def __enter__(self):
        self.create()
        self.attach_policies()
        self.generate_api_keys()

        # wait for API keys to become active
        if self.wait:  # pragma: no cover
            time.sleep(10)
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback) -> None:
        self.delete_api_keys()
        self.detach_policies()
        self.delete()

    def __generate_username(self) -> str:
        suffix = get_random_string(10)
        return f"pitfall-tmp-user-{suffix}"

    def create(self) -> None:
        self.__create_user_response = self.iam_client.create_user(
            Path='/',
            UserName=self.username,
            Tags=[
                {
                    'Key': 'Purpose',
                    'Value': 'integration-testing'
                },
                {
                    'Key': 'CreatedBy',
                    'Value': 'pitfall'
                }
            ]
        )

    def delete(self) -> None:
        self.iam_client.delete_user(UserName=self.username)

    def generate_api_keys(self) -> None:
        self.__create_access_key_response = self.iam_client.create_access_key(
            UserName=self.username
        )

    def delete_api_keys(self) -> None:
        self.iam_client.delete_access_key(
            UserName=self.username,
            AccessKeyId=self.access_key
        )

    def attach_policies(self) -> None:
        for i in self.iam_policies:
            self.iam_client.attach_user_policy(
                PolicyArn=i,
                UserName=self.username
            )

    def detach_policies(self) -> None:
        # we must retrieve the list of policies attached to this user and not rely on
        # the list of policies that we attached upon creation
        r = self.iam_client.list_attached_user_policies(UserName=self.username)

        for i in r["AttachedPolicies"]:
            policy_arn = i["PolicyArn"]
            self.iam_client.detach_user_policy(
                UserName=self.username,
                PolicyArn=policy_arn
            )

    @property
    def access_key(self) -> str:
        return self.__create_access_key_response["AccessKey"]["AccessKeyId"]

    @property
    def secret_key(self) -> str:
        return self.__create_access_key_response["AccessKey"]["SecretAccessKey"]
