# Pulumi Integration Test Framework

[![License](https://img.shields.io/badge/License-Apache-blue.svg)](http://www.apache.org/licenses/LICENSE-2.0)
[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](#)
[![Version](https://img.shields.io/badge/Version-0.0.1-green.svg)](#)
[![Status](https://img.shields.io/badge/Status-alpha-yellow.svg)](#)
[![Coverage Status](https://coveralls.io/repos/github/bincyber/pitfall/badge.svg?branch=master)](https://coveralls.io/github/bincyber/pitfall?branch=master)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=bincyber_pitfall&metric=alert_status)](https://sonarcloud.io/dashboard?id=bincyber_pitfall)
[![CircleCI](https://circleci.com/gh/bincyber/pitfall.svg?style=svg)](https://circleci.com/gh/bincyber/pitfall)

_pitfall_ is a Python integration testing framework for [Pulumi](https://github.com/pulumi/pulumi) Infrastructure as Code. It enables and encourages end to end testing to avoid errors, assumptions, and other pitfalls.

## Installation

_pitfall_ can be installed via pip:

	$ pip install pitfall

## Compatibility

_pitfall_ has been tested against versions 1.2.0 - 1.4.0 of Pulumi and will strive to work with the latest Pulumi release.

**Warning**: this is alpha software. There are no guarantees of backwards compatibility.

## Usage

_pitfall_ is intended to be used in integration tests to verify the desired state of infrastructure provisioned by Pulumi.

It will do the following:

* create a temp directory to store Pulumi code and state
* copy the contents of the current directory (and all subdirectories) to the temp directory
* move into the temp directory
* create a new Pulumi project and stack
* initialize a new Pulumi state file
* install Pulumi plugins
* execute `pulumi preview`
* execute `pulumi up`
* execute `pulumi destroy`
* delete the temp directory

_pitfall_ supports a [context manager](https://docs.python.org/3/reference/datamodel.html#context-managers) to automatically do the above.

_pitfall_ does not use the Pulumi Service backend.

### Basic Example

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

    test_basic_example (test.IntegrationTest) ... ok

    ----------------------------------------------------------------------
    Ran 1 test in 17.669s

    OK


### Advanced Example

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
```

Execute the integration test and ensure it passes:

    $ python -m unittest -v test.py

    test_advanced_example (test.IntegrationTest) ... ok

    ----------------------------------------------------------------------
    Ran 1 test in 19.033s

    OK


### Environment Variables

The following environment variables are supported:

| Environment Variable | Default Value | Description
| -------- | -------- | --------
| PULUMI_HOME | `~/.pulumi` | the location of Pulumi's home directory
| PULUMI_CONFIG_PASSPHRASE | `pulumi` | the password for encrypting secrets

If they are set, they will be inherited by _pitfall_.


## Documentation

TODO

## Testing

[nose2](http://nose2.readthedocs.io/en/latest/) is used for unit and integration testing.

`pulumi` must be installed for tests to pass.

### Unit Tests

Unit tests are located in `/tests`.

To run the unit tests:

    $ make test

### End to End Tests

End to end tests are located in `e2e/`.

1. testing using [localstack](https://github.com/localstack/localstack)

e2e tests that use localstack are located in `e2e/localstack`. These tests require localstack running locally in a container.

To run localstack:

    $ make run-localstack

Run the e2e tests:

    $ make e2e-test-localstack


2. testing using [AWS](https://aws.amazon.com/)

e2e tests that use AWS are located in `e2e/aws`. These tests require an AWS account and valid AWS API keys.

Run the e2e tests:

    $ make e2e-test-aws


## Contributing

We encourage the following contributions at this time: user feedback, documentation, bug reports, and feature requests.

## Acknowledgement

_pitfall_ was built upon the Python libraries listed in its [Pipfile](https://github.com/bincyber/pitfall/blob/master/Pipfile).

## License

Copyright 2019 Ali (@bincyber)

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
