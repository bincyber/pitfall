from pitfall import PulumiIntegrationTest, PulumiIntegrationTestOptions
from pitfall import PulumiConfigurationKey, PulumiPlugin
from pathlib import Path
import botocore
import boto3
import os
import unittest


class TestProvisioningS3Bucket(unittest.TestCase):
    def setUp(self):
        # use localstack to test provisioning
        localstack_s3_endpoint = os.environ.get('LOCALSTACK_S3_ENDPOINT', 'http://localhost:4572')

        self.s3 = boto3.client(
            service_name='s3',
            endpoint_url=localstack_s3_endpoint,
            verify=False,
            aws_access_key_id='integration-test',
            aws_secret_access_key='integration-test',
            config=botocore.client.Config(
                region_name='us-east-1',
                connect_timeout=30,
                read_timeout=30,
                retries={"max_attempts": 1},
                s3={"addressing_style": "path"}
            )
        )

        self.dir = Path(__file__)
        self.pwd = Path.cwd()

    def tearDown(self):
        os.chdir(self.pwd)

    def test_e2e_using_localstack_with_autodestroy(self):
        bucket_name = f"pitfall-localstack-test-bucket-1"

        config = [
            PulumiConfigurationKey(name='local-mode', value=True),
            PulumiConfigurationKey(name='s3-bucket-name', value=bucket_name),
            PulumiConfigurationKey(name='environment', value='test'),
            PulumiConfigurationKey(name='owner', value='@bincyber'),
            PulumiConfigurationKey(name='billing-project', value='integration-testing'),
            PulumiConfigurationKey(name='customer', value=b'ACME Corp', encrypted=True)
        ]

        plugins = [
            PulumiPlugin(kind='resource', name='aws', version='v1.7.0')
        ]

        provisioned_bucket_name = None

        opts = PulumiIntegrationTestOptions(cleanup=True, preview=True, up=True, destroy=True)

        with PulumiIntegrationTest(directory=self.dir, config=config, plugins=plugins, opts=opts) as integration_test:
            outputs = integration_test.get_stack_outputs()

            provisioned_bucket_name = outputs["s3_bucket_name"]
            self.assertTrue(provisioned_bucket_name.startswith(bucket_name))

        # verify that the S3 bucket has been deleted
        with self.assertRaises(botocore.exceptions.ClientError):
            self.s3.head_bucket(Bucket=provisioned_bucket_name)

    def test_e2e_using_localstack_without_autodestroy(self):
        bucket_name = f"pitfall-localstack-test-bucket-2"

        config = [
            PulumiConfigurationKey(name='local-mode', value=True),
            PulumiConfigurationKey(name='s3-bucket-name', value=bucket_name),
            PulumiConfigurationKey(name='environment', value='test'),
            PulumiConfigurationKey(name='owner', value='@bincyber'),
            PulumiConfigurationKey(name='billing-project', value='integration-testing'),
            PulumiConfigurationKey(name='customer', value=b'ACME Corp', encrypted=True)
        ]

        plugins = [
            PulumiPlugin(kind='resource', name='aws', version='v1.7.0')
        ]

        opts = PulumiIntegrationTestOptions(verbose=True, cleanup=False, preview=False, destroy=False)

        with PulumiIntegrationTest(directory=self.dir, config=config, plugins=plugins, opts=opts) as integration_test:
            integration_test.preview.execute()

            pulumi_step = integration_test.preview.steps[0]
            self.assertEqual("create", pulumi_step.op)
            self.assertEqual("aws:s3/bucket:Bucket", pulumi_step.new_state_type)
            self.assertTrue(pulumi_step.new_state_inputs["bucket"].startswith(bucket_name))
            self.assertEqual("private", pulumi_step.new_state_inputs["acl"])

            # execute `pulumi up` to provision resources
            integration_test.up.execute()

            outputs = integration_test.get_stack_outputs()

            # verify that the S3 bucket exists using boto3
            provisioned_bucket_name = outputs["s3_bucket_name"]

            response = self.s3.head_bucket(Bucket=provisioned_bucket_name)
            self.assertIs(dict, type(response))

            # verify required tags have been set by checking the state file
            resources = integration_test.state.resources

            s3_bucket_resource = resources.lookup(key="type", value="aws:s3/bucket:Bucket")[0]
            self.assertEqual("aws:s3/bucket:Bucket", s3_bucket_resource.type)

            required_tags = {"CreatedBy", "CreatedOn", "Environment", "BillingProject", "Owner"}
            self.assertTrue(required_tags <= set(s3_bucket_resource.outputs["tags"]))

            # render the tree of resources
            resources.render_tree()

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

            # `force_destroy` did not work, uplaoded file must be manually deleted
            self.s3.delete_object(
                Bucket=provisioned_bucket_name,
                Key=filename
            )

            # execute `pulumi destroy` to delete the S3 bucket
            integration_test.destroy.execute()

            # verify that the S3 bucket has been deleted
            with self.assertRaises(botocore.exceptions.ClientError):
                self.s3.head_bucket(Bucket=provisioned_bucket_name)
