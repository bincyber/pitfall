### AWS - Advanced S3 Example

This example will demonstrate provisioning a S3 bucket in AWS to host a static website and verifying that its serving the right content.

In `index.html`, write the static HTML page to display to website visitors:

```html
<html>
<head>
    <title>Static Website</title>
    <meta charset="UTF-8">
</head>
<body>
    <p>Provisioned by <a href="https://pulumi.com">Pulumi</a>.</p>
    <p>Tested by <a href="https://github.com/bincyber/pitfall">pitfall</a></p>
</body>
</html>
```

In `__main__.py`, write the Pulumi code to provision the S3 bucket:

```python
from json import dumps
from pathlib import Path
import pulumi_aws as aws
import pulumi


def get_json_bucket_policy(bucket_arn):
    return dumps({
    "Version": "2012-10-17",
    "Statement": [{
        "Sid": "PublicReadGetObject",
        "Effect": "Allow",
        "Principal": "*",
        "Action": ["s3:GetObject"],
        "Resource": f"{bucket_arn}/*"
    }]
})

cfg = pulumi.Config()

bucket_name = cfg.require("s3-bucket-name")

tags = {
    'CreatedBy': 'Pulumi',
    'PulumiProject': pulumi.get_project(),
    'PulumiStack': pulumi.get_stack(),
}

bucket = aws.s3.Bucket(
    resource_name=bucket_name,
    force_destroy=True,
    tags=tags,
    acl="public-read",
    website={
        "index_document":"index.html"
    }
)

policy = bucket.arn.apply(get_json_bucket_policy)

bucket_policy = aws.s3.BucketPolicy(
    resource_name="public_read_get_object",
    bucket=bucket.id,
    policy=policy
)

index_file = Path('./index.html')

bucket_object = aws.s3.BucketObject(
    resource_name="index.html",
    acl="public-read",
    bucket=bucket.id,
    key="index.html",
    content=index_file.read_text(),
    content_type="text/html"
)

url = pulumi.Output.concat("http://", bucket.website_endpoint)

pulumi.export('bucket_name', bucket.id)
pulumi.export('website_url', url)
```

In `test.py`, write the integration test:
```python
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
            self.assertEqual(resources.providers["pulumi:providers:aws"], 3)

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
```

Execute the integration test and ensure it passes:

    $ python -m unittest -v test.py

    test_advanced_s3_example (test.IntegrationTest) ... ok

    ----------------------------------------------------------------------
    Ran 1 test in 19.033s

    OK
