from pitfall.helpers.aws import utils
import unittest


class TestAWSHelperUtils(unittest.TestCase):
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
