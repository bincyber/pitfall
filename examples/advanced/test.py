from pitfall import PulumiIntegrationTest, PulumiIntegrationTestOptions
from pitfall import PulumiConfigurationKey, PulumiPlugin
from pathlib import Path
import boto3
import requests
import unittest


class IntegrationTest(unittest.TestCase):
    def test_advanced_example(self):
        region = "us-east-1"
        bucket_name = "pitfall-advanced-example"

        config = [
            PulumiConfigurationKey(name='aws:region', value=region),
            PulumiConfigurationKey(name='s3-bucket-name', value=bucket_name)
        ]

        plugins = [
            PulumiPlugin(kind='resource', name='aws', version='v1.7.0')
        ]

        opts = PulumiIntegrationTestOptions(cleanup=True, preview=False, up=False, destroy=False)

        directory = Path(__file__)

        with PulumiIntegrationTest(directory=directory, config=config, plugins=plugins, opts=opts) as t:
            # execute `pulumi preview`
            t.preview.execute()

            # verify that 3 resources will be provisioned
            pulumi_steps = t.preview.steps
            self.assertEqual(len(pulumi_steps), 3)

            for step in pulumi_steps:
                self.assertEqual("create", step.op)

            # execute `pulumi up`
            t.up.execute()

            # verify that 3 resources have been provisioned
            resources = t.state.resources
            self.assertEqual(len(resources), 3)

            # get the bucket_name and website_url from the stack outputs
            stack_outputs = t.get_stack_outputs()

            # verify that the bucket was provisioned
            bucket = stack_outputs["bucket_name"]

            s3 = boto3.client(service_name="s3")
            s3.head_bucket(Bucket=bucket)

            # verify that the bucket is hosting a website and serving the uploaded index.html file
            index_html_file = Path('./index.html')

            url = stack_outputs["website_url"]

            r = requests.get(url, timeout=5)
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.text, index_html_file.read_text())

            # execute `pulumi destroy`
            t.destroy.execute()
