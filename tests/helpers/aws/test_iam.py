from pitfall.helpers.aws import iam
from moto import mock_iam
import boto3
import json
import os
import unittest


class TestTemporaryUser(unittest.TestCase):
    def setUp(self):
        # set AWS credentials for moto
        os.environ["AWS_ACCESS_KEY_ID"]     = "test"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "test"

        self.base_arn = "arn:aws:iam::123456789012"
        self.policies = [f"{self.base_arn}:policy/test"]

        self.tmp_user = iam.TemporaryUser(policies=self.policies)
        self.username = self.tmp_user.username

    def create_test_iam_policy(self):
        self.tmp_user.iam_client.create_policy(
            PolicyName="test",
            PolicyDocument=json.dumps({
                "Version": "2012-10-17",
                "Statement": [{
                    "Action": "*",
                    "Resource": "*",
                    "Effect": "Allow"
                }]
            })
        )

    def test_username(self):
        self.assertTrue(self.tmp_user.username.startswith('pitfall-tmp-user-'))

    @mock_iam
    def test_create(self):
        self.tmp_user.create()

        r = self.tmp_user._TemporaryUser__create_user_response

        sub_tests = [
            {
                "msg": "verify the username of the created user",
                "expected": self.username,
                "actual": r["User"]["UserName"]
            },
            {
                "msg": "verify the ARN of the created user",
                "expected": f"{self.base_arn}:user/{self.username}",
                "actual": r["User"]["Arn"]
            }
        ]

        for i in sub_tests:
            with self.subTest(msg=i["msg"]):
                self.assertEqual(i["expected"], i["actual"])

    @mock_iam
    def test_delete(self):
        self.tmp_user.create()
        self.tmp_user.delete()

        with self.assertRaises(self.tmp_user.iam_client.exceptions.NoSuchEntityException):
            self.tmp_user.iam_client.get_user(UserName=self.username)

    @mock_iam
    def test_generate_api_keys(self):
        self.tmp_user.create()
        self.tmp_user.generate_api_keys()

        r = self.tmp_user._TemporaryUser__create_access_key_response

        with self.subTest("verify Access Key & Secret Key are returned"):
            for i in ["AccessKeyId", "SecretAccessKey"]:
                self.assertIn(i, r["AccessKey"])

        with self.subTest("verify Access Key is set as a Class property"):
            access_key = r["AccessKey"]["AccessKeyId"]
            self.assertEqual(access_key, self.tmp_user.access_key)

        with self.subTest("verify Secret Key is set as a Class property"):
            secret_key = r["AccessKey"]["SecretAccessKey"]
            self.assertEqual(secret_key, self.tmp_user.secret_key)

    @mock_iam
    def test_delete_api_keys(self):
        self.tmp_user.create()
        self.tmp_user.generate_api_keys()
        self.tmp_user.delete_api_keys()

        r = self.tmp_user.iam_client.list_access_keys(UserName=self.username)
        self.assertEqual(len(r["AccessKeyMetadata"]), 0)

    @mock_iam
    def test_attach_policies(self):
        self.tmp_user.create()
        self.create_test_iam_policy()
        self.tmp_user.attach_policies()

        r = self.tmp_user.iam_client.list_attached_user_policies(UserName=self.username)
        self.assertEqual(len(r["AttachedPolicies"]), 1)

    @mock_iam
    def test_detach_policies(self):
        self.tmp_user.create()
        self.create_test_iam_policy()
        self.tmp_user.attach_policies()
        self.tmp_user.detach_policies()

        r = self.tmp_user.iam_client.list_attached_user_policies(UserName=self.username)
        self.assertEqual(len(r["AttachedPolicies"]), 0)

    @mock_iam
    def test_context_manager(self):
        iam_client = boto3.client('iam')

        self.create_test_iam_policy()

        username = ""
        with iam.TemporaryUser(policies=self.policies, wait=False) as tmp_user:
            username = tmp_user.username

            with self.subTest("verify IAM user was provisioned"):
                iam_client.get_user(UserName=username)

            with self.subTest("verify Access Key & Secret Key were generated"):
                r = iam_client.list_access_keys(UserName=username)
                self.assertEqual(len(r["AccessKeyMetadata"]), 1)

            with self.subTest("verify IAM Policies were attached"):
                r = iam_client.list_attached_user_policies(UserName=username)
                self.assertEqual(len(r["AttachedPolicies"]), 1)

        # verify that the IAM user was deleted
        with self.assertRaises(iam_client.exceptions.NoSuchEntityException):
            iam_client.get_user(UserName=username)
