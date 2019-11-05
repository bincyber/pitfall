from pitfall import PulumiIntegrationTest, PulumiIntegrationTestOptions
from pitfall import PulumiConfigurationKey, PulumiPlugin
from pathlib import Path
import botocore
import boto3
import os
import time
import unittest


class TestPulumiCode(unittest.TestCase):
    def setUp(self):
        self.s3  = boto3.client(service_name="s3")
        self.dir = Path(__file__)
        self.pwd = Path.cwd()

        self.plugins = [
            PulumiPlugin(kind='resource', name='aws', version='v1.7.0')
        ]

    def tearDown(self):
        os.chdir(self.pwd)

    def test_aws_provision_s3_bucket_with_auto_cleanup_destroy(self):
        region      = "us-east-2"
        bucket_name = f"pitfall-test-bucket-1"

        config = [
            PulumiConfigurationKey(name='aws:region', value=region),
            PulumiConfigurationKey(name='s3-bucket-name', value=bucket_name),
            PulumiConfigurationKey(name='environment', value='test'),
            PulumiConfigurationKey(name='owner', value='@bincyber'),
            PulumiConfigurationKey(name='billing-project', value='integration-testing'),
            PulumiConfigurationKey(name='customer', value=b'ACME Corp', encrypted=True)
        ]

        provisioned_bucket_name = None

        opts = PulumiIntegrationTestOptions(cleanup=True, preview=True, up=True, destroy=True)

        with PulumiIntegrationTest(directory=self.dir, config=config, plugins=self.plugins, opts=opts) as integration_test:
            outputs = integration_test.get_stack_outputs()

            provisioned_bucket_name = outputs["s3_bucket_name"]
            self.assertTrue(provisioned_bucket_name.startswith(bucket_name))

        # verify that the S3 bucket has been deleted
        with self.assertRaises(botocore.exceptions.ClientError):
            self.s3.head_bucket(Bucket=provisioned_bucket_name)

    def test_aws_provision_s3_bucket_without_auto_cleanup_destroy(self):
        region = "us-east-1"
        bucket_name = f"pitfall-test-bucket-2"

        config = [
            PulumiConfigurationKey(name='aws:region', value=region),
            PulumiConfigurationKey(name='s3-bucket-name', value=bucket_name),
            PulumiConfigurationKey(name='environment', value='test'),
            PulumiConfigurationKey(name='owner', value='@bincyber'),
            PulumiConfigurationKey(name='billing-project', value='integration-testing'),
            PulumiConfigurationKey(name='customer', value=b'ACME Corp', encrypted=True)
        ]

        opts = PulumiIntegrationTestOptions(verbose=True, cleanup=False, preview=False, destroy=False)

        with PulumiIntegrationTest(directory=self.dir, config=config, plugins=self.plugins, opts=opts) as integration_test:
            integration_test.preview.execute()

            pulumi_step = integration_test.preview.steps[0]
            self.assertEqual("create", pulumi_step.op)
            self.assertEqual("aws:s3/bucket:Bucket", pulumi_step.new_state_type)
            self.assertTrue(pulumi_step.new_state_inputs["bucket"].startswith(bucket_name))
            self.assertEqual("private", pulumi_step.new_state_inputs["acl"])

            integration_test.up.execute()

            outputs = integration_test.get_stack_outputs()

            # verify that the S3 bucket exists using boto3
            provisioned_bucket_name = outputs["s3_bucket_name"]

            response = self.s3.head_bucket(Bucket=provisioned_bucket_name)
            self.assertIs(dict, type(response))

            expected = response["ResponseMetadata"]["HTTPHeaders"]["x-amz-bucket-region"]
            actual   = region
            self.assertEqual(expected, actual)

            # verify required tags have been set by checking the state file
            resources = integration_test.state.resources

            s3_bucket_resource = resources.lookup(key="type", value="aws:s3/bucket:Bucket")[0]
            self.assertEqual("aws:s3/bucket:Bucket", s3_bucket_resource.type)

            required_tags = {"CreatedBy", "CreatedOn", "Environment", "BillingProject", "Owner"}
            self.assertTrue(required_tags <= set(s3_bucket_resource.outputs["tags"]))

            # upload __main__.py to the S3 bucket
            filename       = "__main__.py"
            file           = self.dir.parent.joinpath(filename)
            content_length = len(file.read_bytes())
            content_type   = "application/x-python-code"

            self.s3.put_object(
                ACL="private",
                Bucket=provisioned_bucket_name,
                Body=file.read_bytes(),
                Key=filename,
                ContentLength=content_length,
                ContentType=content_type
            )

            response = self.s3.head_object(
                Bucket=provisioned_bucket_name,
                Key=filename
            )

            expected = response["ContentLength"]
            actual   = content_length
            self.assertEqual(expected, actual)

            expected = response["ContentType"]
            actual   = content_type
            self.assertEqual(expected, actual)

            # execute `pulumi up` again for idempotency test
            integration_test.up.execute(expect_no_changes=True)

            # execute `pulumi destroy` to delete S3 bucket
            integration_test.destroy.execute()

            # wait for bucket deletion
            time.sleep(5)

            # verify that the S3 bucket has been deleted
            with self.assertRaises(botocore.exceptions.ClientError):
                self.s3.head_bucket(Bucket=provisioned_bucket_name)
