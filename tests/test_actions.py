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

from contextlib import redirect_stdout
from io import StringIO
from pitfall.actions import PulumiStep, PulumiPreview, PulumiUp, PulumiDestroy
from pitfall import exceptions
from pitfall import utils
from pathlib import Path
from unittest.mock import patch, MagicMock
import json
import subprocess
import unittest


class TestPulumiPreview(unittest.TestCase):
    def setUp(self):
        self.pulumi_preview = PulumiPreview()
        self.args = ['pulumi', 'preview', '--non-interactive', '--json']

    def tearDown(self):
        pass

    def test_execute(self):
        stdout = b'{"config":{}, "steps":[], "changeSummary":{"create": 1}}'
        stderr = b'warning: A new version of Pulumi is available.'
        json_stdout = json.loads(stdout)

        completed_process = subprocess.CompletedProcess(args=self.args, returncode=0, stdout=stdout, stderr=stderr)

        with patch('subprocess.run', MagicMock(return_value=completed_process)):
            p = self.pulumi_preview.execute()
            self.assertIsInstance(p, subprocess.CompletedProcess)
            self.assertEqual(0, p.returncode)

        self.assertIsInstance(self.pulumi_preview.stdout, dict)
        self.assertDictEqual(json_stdout, self.pulumi_preview.stdout)

        dict_keys = ["config", "steps", "changeSummary"]
        for expected in dict_keys:
            self.assertIn(expected, self.pulumi_preview.stdout)

        expected = utils.decode_utf8(stderr)
        self.assertIsNot(bytes, type(self.pulumi_preview.stderr))
        self.assertIsInstance(self.pulumi_preview.stderr, str)
        self.assertEqual(expected, self.pulumi_preview.stderr)

    def test_execute_with_verbosity(self):
        self.pulumi_preview.verbose = True

        stdout = b'{"config":{}, "steps":[], "changeSummary":{"create": 1}}'

        completed_process = subprocess.CompletedProcess(args=self.args, returncode=0, stdout=stdout, stderr=b'')

        with patch('subprocess.run', MagicMock(return_value=completed_process)):
            b = StringIO()
            with redirect_stdout(b):
                self.pulumi_preview.execute()

            output = b.getvalue()
            self.assertTrue(output.startswith('$ pulumi preview --non-interactive --json\n'))

    def test_execute_raises_exception(self):
        stdout = b'{"config":{}, "steps":[], "diagnostics":[{"message":"error: Missing required configuration variable...", "severity": "error"}]}'
        json_stdout = json.loads(stdout)

        completed_process = subprocess.CompletedProcess(args=self.args, returncode=255, stdout=stdout, stderr=b'')

        err = None
        with patch('subprocess.run', MagicMock(return_value=completed_process)):
            try:
                self.pulumi_preview.execute()
            except exceptions.PulumiPreviewExecError as e:
                err = e.args[0]

        output = json.loads(err)
        self.assertIsInstance(output, dict)
        self.assertDictEqual(json_stdout, output)

        dict_keys = ["config", "steps", "diagnostics"]
        for expected in dict_keys:
            self.assertIn(expected, output)

        self.assertIsInstance(self.pulumi_preview.diagnostics, list)
        self.assertEqual(1, len(self.pulumi_preview.diagnostics))

        expected = "error: Missing required configuration variable..."
        self.assertEqual(expected, self.pulumi_preview.diagnostics[0]["message"])

    def test_execute_raises_exception_stderr(self):
        stderr = b'error: failed to load checkpoint...'

        completed_process = subprocess.CompletedProcess(args=self.args, returncode=255, stdout=b'', stderr=stderr)

        with patch('subprocess.run', MagicMock(return_value=completed_process)):
            try:
                self.pulumi_preview.execute()
            except exceptions.PulumiPreviewExecError as e:
                err = e.args[0]

            self.assertIsInstance(err, str)
            self.assertEqual(err, stderr.decode('utf-8'))

    def test_config(self):
        config = {"aws:region": "us-east-1", "pitfall:environment": "integration-test"}
        stdout = b'{"config":{"aws:region": "us-east-1", "pitfall:environment": "integration-test"}, "steps":[], "changeSummary":{}}'

        self.pulumi_preview._stdout = stdout
        self.assertIsInstance(self.pulumi_preview.config, dict)
        self.assertDictEqual(config, self.pulumi_preview.config)

    def test_steps(self):
        stdout = Path(__file__).parent.joinpath('test_data/preview.json').read_bytes()

        self.pulumi_preview._stdout = stdout

        steps = self.pulumi_preview.steps
        self.assertIsInstance(steps, list)
        self.assertEqual(1, len(steps))

        pulumi_step = steps[0]
        self.assertIsInstance(pulumi_step, PulumiStep)
        self.assertEqual("update", pulumi_step.op)
        self.assertEqual("aws:s3/bucket:Bucket", pulumi_step.new_state_type)
        self.assertEqual("aws:s3/bucket:Bucket", pulumi_step.old_state_type)
        self.assertEqual("pitfall-1174b83f846341908354ffc0-c4f911a", pulumi_step.new_state_inputs["bucket"])
        self.assertEqual({}, pulumi_step.new_state_outputs)
        self.assertEqual("private", pulumi_step.old_state_inputs["acl"])
        self.assertEqual("pitfall-1174b83f846341908354ffc0-c4f911a.s3.amazonaws.com", pulumi_step.old_state_outputs["bucketDomainName"])
        self.assertEqual("tags", pulumi_step.diff_reasons[0])

    def test_change_summary(self):
        create = 1
        same   = 2
        update = 1
        delete = 3

        stdout = b'{"config":{}, "steps":[], "changeSummary":{"create": %d, "same": %d, "update": %d, "delete": %d}}' % (create, same, update, delete)

        self.pulumi_preview._stdout = stdout

        self.assertEqual(create, self.pulumi_preview.create)
        self.assertEqual(same, self.pulumi_preview.same)
        self.assertEqual(update, self.pulumi_preview.update)
        self.assertEqual(delete, self.pulumi_preview.delete)


class TestPulumiUp(unittest.TestCase):
    def setUp(self):
        self.pulumi_up = PulumiUp()
        self.args = ['pulumi', 'up', '--non-interactive', '--skip-preview']

    def tearDown(self):
        pass

    def test_execute(self):
        stdout = b'''Updating (pit-stack-981495048f964a8f):

 +  pulumi:pulumi:Stack pit-project-9106be1dfe6947fa-pit-stack-981495048f964a8f creating
 +  aws:s3:Bucket pitfall-test-bucket creating
 +  aws:s3:Bucket pitfall-test-bucket created
 +  pulumi:pulumi:Stack pit-project-9106be1dfe6947fa-pit-stack-981495048f964a8f created

Outputs:
    s3_bucket_name: "pitfall-test-bucket-09060ae"

Resources:
    + 2 created

Duration: 10s

Permalink: file:///Users/aliibrahim/Devel/local/pit/pit-cocobiek/.pulumi/stacks/pit-stack-981495048f964a8f.json
'''

        stderr = b'warning: A new version of Pulumi is available...'

        completed_process = subprocess.CompletedProcess(args=self.args, returncode=0, stdout=stdout, stderr=stderr)

        with patch('subprocess.run', MagicMock(return_value=completed_process)):
            p = self.pulumi_up.execute()
            self.assertIsInstance(p, subprocess.CompletedProcess)
            self.assertEqual(0, p.returncode)

        expected = utils.decode_utf8(stdout)
        self.assertIsNot(bytes, type(self.pulumi_up.stdout))
        self.assertIsInstance(self.pulumi_up.stdout, str)
        self.assertEqual(expected, self.pulumi_up.stdout)

        expected = utils.decode_utf8(stderr)
        self.assertIsNot(bytes, type(self.pulumi_up.stderr))
        self.assertIsInstance(self.pulumi_up.stderr, str)
        self.assertEqual(expected, self.pulumi_up.stderr)

    def test_execute_with_verbosity(self):
        self.pulumi_up.verbose = True

        stdout = b'Updating (pit-stack-981495048f964a8f):'

        completed_process = subprocess.CompletedProcess(args=self.args, returncode=0, stdout=stdout, stderr=b'')

        with patch('subprocess.run', MagicMock(return_value=completed_process)):
            b = StringIO()
            with redirect_stdout(b):
                self.pulumi_up.execute()

            output = b.getvalue()
            self.assertTrue(output.startswith('$ pulumi up --non-interactive --skip-preview\n'))

    def test_execute_raises_exception(self):
        stdout = b'''Updating (pit-stack-1e890f9e54c44aef):

 +  pulumi:pulumi:Stack pit-project-e6abfe91b6a04b1b-pit-stack-1e890f9e54c44aef creating
    aws:s3:Bucket pitfall-test-bucket  error: No valid credential sources found for AWS Provider.
 +  pulumi:pulumi:Stack pit-project-e6abfe91b6a04b1b-pit-stack-1e890f9e54c44aef created
    aws:s3:Bucket pitfall-test-bucket **failed** 1 error

Diagnostics:
  aws:s3:Bucket (pitfall-test-bucket):
    error: No valid credential sources found for AWS Provider.
        Please see https://terraform.io/docs/providers/aws/index.html for more information on
        providing credentials for the AWS Provider

Resources:
    + 1 created

Duration: 3s
'''

        stderr = b'warning: A new version of Pulumi is available...'

        completed_process = subprocess.CompletedProcess(args=self.args, returncode=255, stdout=stdout, stderr=stderr)

        with patch('subprocess.run', MagicMock(return_value=completed_process)):
            with self.assertRaises(exceptions.PulumiUpExecError):
                self.pulumi_up.execute()

            try:
                self.pulumi_up.execute()
            except exceptions.PulumiUpExecError as err:
                expected = utils.decode_utf8(stdout)
                actual = err.args[0]
                self.assertEqual(expected, actual)

            expected = utils.decode_utf8(stdout)
            self.assertEqual(expected, self.pulumi_up.stdout)

            expected = utils.decode_utf8(stderr)
            self.assertEqual(expected, self.pulumi_up.stderr)

    def test_execute_raises_exception_stderr(self):
        stderr = b'error: failed to load checkpoint...'

        completed_process = subprocess.CompletedProcess(args=self.args, returncode=255, stdout=b'', stderr=stderr)

        with patch('subprocess.run', MagicMock(return_value=completed_process)):
            try:
                self.pulumi_up.execute(expect_no_changes=True)
            except exceptions.PulumiUpExecError as e:
                err = e.args[0]

            self.assertIsInstance(err, str)
            self.assertEqual(err, stderr.decode('utf-8'))


class TestPulumiDestroy(unittest.TestCase):
    def setUp(self):
        self.pulumi_destroy = PulumiDestroy()
        self.args = ["pulumi", "destroy", "--non-interactive", "--skip-preview"]

    def tearDown(self):
        pass

    def test_execute(self):
        stdout = b'''Destroying (pit-stack-f68224b0594e4baa):

 -  aws:s3:Bucket pitfall-test-bucket deleting
 -  aws:s3:Bucket pitfall-test-bucket deleted
 -  pulumi:pulumi:Stack pit-project-574b710378c44755-pit-stack-f68224b0594e4baa deleting
 -  pulumi:pulumi:Stack pit-project-574b710378c44755-pit-stack-f68224b0594e4baa deleted

Resources:
    - 2 deleted

Duration: 5s

Permalink: file:///Users/aliibrahim/Devel/local/pit/pit-m4zc0bhe/.pulumi/stacks/pit-stack-f68224b0594e4baa.json
The resources in the stack have been deleted, but the history and configuration associated with the stack are still maintained.
If you want to remove the stack completely, run 'pulumi stack rm pit-stack-f68224b0594e4baa'.'''

        stderr = b'warning: A new version of Pulumi is available...'

        completed_process = subprocess.CompletedProcess(args=self.args, returncode=0, stdout=stdout, stderr=stderr)

        with patch('subprocess.run', MagicMock(return_value=completed_process)):
            p = self.pulumi_destroy.execute()
            self.assertIsInstance(p, subprocess.CompletedProcess)
            self.assertEqual(0, p.returncode)

        expected = utils.decode_utf8(stdout)
        self.assertIsNot(bytes, type(self.pulumi_destroy.stdout))
        self.assertIsInstance(self.pulumi_destroy.stdout, str)
        self.assertEqual(expected, self.pulumi_destroy.stdout)

        expected = utils.decode_utf8(stderr)
        self.assertIsNot(bytes, type(self.pulumi_destroy.stderr))
        self.assertIsInstance(self.pulumi_destroy.stderr, str)
        self.assertEqual(expected, self.pulumi_destroy.stderr)

    def test_execute_with_verbosity(self):
        self.pulumi_destroy.verbose = True

        stdout = b'Destroying (pit-stack-981495048f964a8f):'
        stderr = b'warning: A new version of Pulumi is available.'

        completed_process = subprocess.CompletedProcess(args=self.args, returncode=0, stdout=stdout, stderr=stderr)

        with patch('subprocess.run', MagicMock(return_value=completed_process)):
            b = StringIO()
            with redirect_stdout(b):
                self.pulumi_destroy.execute()

            output = b.getvalue()
            self.assertTrue(output.startswith('$ pulumi destroy --non-interactive --skip-preview\n'))

    def test_execute_raises_exception(self):
        stdout = b'''Destroying (pit-stack-f68224b0594e4baa):

 -  aws:s3:Bucket pitfall-test-bucket deleting
@ destroying....
 -  aws:s3:Bucket pitfall-test-bucket deleting error: Plan apply failed: No valid credential sources found for AWS Provider.
 -  aws:s3:Bucket pitfall-test-bucket **deleting failed** error: Plan apply failed: No valid credential sources found for AWS Provider.
    pulumi:pulumi:Stack pit-project-574b710378c44755-pit-stack-f68224b0594e4baa  error: update failed
    pulumi:pulumi:Stack pit-project-574b710378c44755-pit-stack-f68224b0594e4baa **failed** 1 error

Diagnostics:
  aws:s3:Bucket (pitfall-test-bucket):
    error: Plan apply failed: No valid credential sources found for AWS Provider.
        Please see https://terraform.io/docs/providers/aws/index.html for more information on
        providing credentials for the AWS Provider

  pulumi:pulumi:Stack (pit-project-574b710378c44755-pit-stack-f68224b0594e4baa):
    error: update failed'''

        stderr = b'warning: A new version of Pulumi is available...'

        completed_process = subprocess.CompletedProcess(args=self.args, returncode=255, stdout=stdout, stderr=stderr)

        with patch('subprocess.run', MagicMock(return_value=completed_process)):
            with self.assertRaises(exceptions.PulumiDestroyExecError):
                self.pulumi_destroy.execute()

            try:
                self.pulumi_destroy.execute()
            except exceptions.PulumiDestroyExecError as err:
                expected = utils.decode_utf8(stdout)
                actual   = err.args[0]
                self.assertEqual(expected, actual)

            expected = utils.decode_utf8(stdout)
            self.assertEqual(expected, self.pulumi_destroy.stdout)

            expected = utils.decode_utf8(stderr)
            self.assertEqual(expected, self.pulumi_destroy.stderr)

    def test_execute_raises_exception_stderr(self):
        stderr = b'error: failed to load checkpoint...'

        completed_process = subprocess.CompletedProcess(args=self.args, returncode=255, stdout=b'', stderr=stderr)

        with patch('subprocess.run', MagicMock(return_value=completed_process)):
            try:
                self.pulumi_destroy.execute()
            except exceptions.PulumiDestroyExecError as e:
                err = e.args[0]

            self.assertIsInstance(err, str)
            self.assertEqual(err, stderr.decode('utf-8'))
