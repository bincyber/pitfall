from pitfall.helpers.aws import utils
from moto import mock_ec2
from unittest.mock import patch, MagicMock
import os
import unittest


class TestAWSHelperUtils(unittest.TestCase):
    def setUp(self):
        # set AWS credentials for moto
        os.environ["AWS_ACCESS_KEY_ID"]     = "test"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "test"

    def test_extract_tags(self):
        tag_set = [
            {
                'Key': 'CreatedBy',
                'Value': 'Pulumi'
            },
            {
                'Key': 'Environment',
                'Value': 'test'
            },
            {
                'Key': 'BillingProject',
                'Value': 'integration-testing'
            }
        ]

        expected = {
            'Environment': 'test',
            'CreatedBy': 'Pulumi',
            'BillingProject': 'integration-testing'
        }
        actual = utils.extract_tags(tag_set)
        self.assertDictEqual(expected, actual)

    @mock_ec2
    def test_get_all_regions(self):
        regions = utils.get_all_regions()
        self.assertIsInstance(regions, list)
        for i in ["us-east-1", "us-west-1", "eu-west-1", "ca-central-1"]:
            self.assertIn(i, regions)
        self.assertGreater(len(regions), 8)

    @mock_ec2
    def test_get_random_region(self):
        with patch('random.choice', MagicMock(return_value="us-east-1")):
            expected = utils.get_random_region()
            self.assertEqual(expected, "us-east-1")
