### AWS - Basic S3 Example

This example will demonstrate provisioning a S3 bucket in AWS and verifying that required tags have been set.

In `__main__.py`, write the Pulumi code to provision the S3 bucket:
```python
import pulumi_aws as aws
import pulumi

cfg = pulumi.Config()

bucket_name = cfg.require("s3-bucket-name")

required_tags = {
    'CreatedBy': 'Pulumi',
    'PulumiProject': pulumi.get_project(),
    'PulumiStack': pulumi.get_stack(),
}

bucket = aws.s3.Bucket(
    resource_name=bucket_name,
    acl="private",
    force_destroy=True,
    tags=required_tags
)

pulumi.export('bucket_name', bucket.id)
```

In `test.py`, write the integration test:
```python
from pitfall import PulumiIntegrationTest, PulumiIntegrationTestOptions
from pitfall import PulumiConfigurationKey, PulumiPlugin
from pathlib import Path
import boto3
import unittest


class IntegrationTest(unittest.TestCase):
    def test_basic_example(self):
        region = "us-east-1"
        bucket_name = "pitfall-basic-example"

        config = [
            PulumiConfigurationKey(name='aws:region', value=region),
            PulumiConfigurationKey(name='s3-bucket-name', value=bucket_name)
        ]

        plugins = [
            PulumiPlugin(kind='resource', name='aws', version='v1.7.0')
        ]

        opts = PulumiIntegrationTestOptions(cleanup=True, preview=True, up=True, destroy=True)

        directory = Path(__file__)

        # use the context manager to automatically handle test setup and execution of pulumi preview/up/destroy
        with PulumiIntegrationTest(directory=directory, config=config, plugins=plugins, opts=opts) as t:
            # get the name of the bucket from the stack's outputs
            stack_outputs = t.get_stack_outputs()

            bucket = stack_outputs["bucket_name"]

            # use boto3 to perform verifications
            s3 = boto3.client(service_name="s3")

            # verify that the bucket was provisioned in us-east-1
            r = s3.head_bucket(Bucket=bucket)

            bucket_region = r["ResponseMetadata"]["HTTPHeaders"]["x-amz-bucket-region"]
            self.assertEqual(region, bucket_region)

            # verify that the bucket has the required tags set
            required_tags = {"CreatedBy", "PulumiProject", "PulumiStack"}

            r = s3.get_bucket_tagging(Bucket=bucket)

            set_tags = {i["Key"]:i["Value"] for i in r["TagSet"]}

            self.assertTrue(required_tags <= set(set_tags))
```

Execute the integration test and ensure it passes:

    $ python -m unittest -v test.py

    test_basic_s3_example (test.IntegrationTest) ... ok

    ----------------------------------------------------------------------
    Ran 1 test in 17.669s

    OK
