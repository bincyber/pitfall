from e2e import utils
from pitfall import PulumiIntegrationTest, PulumiIntegrationTestOptions
from pitfall import PulumiConfigurationKey, PulumiPlugin
from pathlib import Path
import boto3
import os
import unittest


class IntegrationTest(unittest.TestCase):
    def setUp(self):
        self.pwd = Path.cwd()
        self.required_tags = {"CreatedBy", "Environment", "BillingProject", "PulumiProject", "PulumiStack"}

    def tearDown(self):
        os.chdir(self.pwd)

    def test_component_resource(self):
        region   = "us-west-2"
        vpc_name = "pitfall-test-vpc"
        vpc_cidr = "10.0.0.0/16"
        subnets  = 2
        prefix   = 20

        config = [
            PulumiConfigurationKey(name='aws:region', value=region),
            PulumiConfigurationKey(name='environment', value='test'),
            PulumiConfigurationKey(name='billing-project', value='integration-testing'),
            PulumiConfigurationKey(name='vpc-name', value=vpc_name),
            PulumiConfigurationKey(name='vpc-cidr', value=vpc_cidr),
            PulumiConfigurationKey(name='subnets', value=subnets),
            PulumiConfigurationKey(name='prefix', value=prefix),
        ]

        plugins = [
            PulumiPlugin(kind='resource', name='aws', version='v1.7.0')
        ]

        opts = PulumiIntegrationTestOptions(verbose=True, cleanup=False, preview=True, up=False, destroy=True)

        directory = Path(__file__)

        with PulumiIntegrationTest(directory=directory, config=config, plugins=plugins, opts=opts) as t:
            # verify that 9 create steps are planned
            steps = t.preview.steps
            self.assertEqual(9, len(steps))  # includes step for create ComponentResource:VpcWithPublicSubnets

            for pulumi_step in steps:
                self.assertEqual("create", pulumi_step.op)

            # provision resources
            t.up.execute()

            # verify that 8 resources were provisioned
            resources = t.state.resources
            self.assertEqual(8, len(resources))

            outputs = t.get_stack_outputs()

            # use boto3 to verify desired state
            ec2 = boto3.client('ec2')

            # verify that the VPC CIDR is correct
            vpc_id = outputs["vpc"]["id"]

            r = ec2.describe_vpcs(VpcIds=[vpc_id])

            provisioned_vpc = r["Vpcs"][0]
            self.assertEqual(provisioned_vpc["CidrBlock"], vpc_cidr)

            # verify that the required tags are set on the VPC
            tags = utils.extract_tags_from_aws_resource(provisioned_vpc)
            self.assertTrue(self.required_tags <= set(tags))

            # verify that 2 subnets were provisioned
            self.assertEqual(2, len(outputs["public_subnets"]))

            # verify that the subnet CIDRs are /20 prefixes
            subnet_ids = [i["id"] for i in outputs["public_subnets"]]
            r = ec2.describe_subnets(SubnetIds=subnet_ids)

            expected_cidrs = ["10.0.0.0/20", "10.0.16.0/20"]
            actual_cidrs   = [i["CidrBlock"] for i in r["Subnets"]]
            self.assertListEqual(expected_cidrs, sorted(actual_cidrs))

            # verify that the route table belongs to the VPC
            rtb_id = outputs["public_route_table"]["id"]

            r = ec2.describe_route_tables(RouteTableIds=[rtb_id])

            provisioned_rtb = r["RouteTables"][0]

            self.assertEqual(vpc_id, provisioned_rtb["VpcId"])

            # verify that the route table has a default route set to the Internet Gateway
            igw_id = outputs["internet_gateway"]["id"]

            self.assertEqual(2, len(provisioned_rtb["Routes"]))

            default_route = provisioned_rtb["Routes"][-1]
            self.assertEqual(igw_id, default_route["GatewayId"])
            self.assertEqual("0.0.0.0/0", default_route["DestinationCidrBlock"])

            # verify that the required tags are set on the route table
            tags = utils.extract_tags_from_aws_resource(provisioned_rtb)
            self.assertTrue(self.required_tags <= set(tags))
