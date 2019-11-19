### AWS - VPC Component Resource Example

This example will demonstrate provisioning a VPC with public subnets in AWS using a [Pulumi Component](https://www.pulumi.com/docs/intro/concepts/programming-model/#components).

Refer to [`component.py`](https://github.com/bincyber/pitfall/blob/master/examples/aws-vpc/component.py) for the Component Resource.

In `__main__.py`, write the Pulumi code to provision the VPC:
```python
from component import VpcWithPublicSubnets
import pulumi


cfg = pulumi.Config()

vpc_name = cfg.require("vpc-name")
vpc_cidr = cfg.require("vpc-cidr")
subnets  = cfg.require_int("subnets")
prefix   = cfg.require_int("prefix")

tags = {
    'Environment': cfg.require('environment'),
    'BillingProject': cfg.require('billing-project'),
    'CreatedBy': 'Pulumi',
    'PulumiProject': pulumi.get_project(),
    'PulumiStack': pulumi.get_stack(),
}

component = VpcWithPublicSubnets(
    name=vpc_name,
    cidr=vpc_cidr,
    subnets=subnets,
    prefix=prefix,
    tags=tags
)

component.export()
```

In `test.py`, write the integration test:
```python
from pitfall.helpers.aws import utils
from pitfall import PulumiIntegrationTest, PulumiIntegrationTestOptions
from pitfall import PulumiConfigurationKey, PulumiPlugin
from pathlib import Path
import boto3
import os
import unittest


class IntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.region   = utils.get_random_region()
        vpc_name = "pitfall-test-vpc"
        cls.vpc_cidr = "10.0.0.0/16"
        subnets  = 2
        prefix   = 20

        config = [
            PulumiConfigurationKey(name='aws:region', value=cls.region),
            PulumiConfigurationKey(name='environment', value='test'),
            PulumiConfigurationKey(name='billing-project', value='integration-testing'),
            PulumiConfigurationKey(name='vpc-name', value=vpc_name),
            PulumiConfigurationKey(name='vpc-cidr', value=cls.vpc_cidr),
            PulumiConfigurationKey(name='subnets', value=subnets),
            PulumiConfigurationKey(name='prefix', value=prefix),
        ]

        plugins = [
            PulumiPlugin(kind='resource', name='aws', version='v1.7.0')
        ]

        opts = PulumiIntegrationTestOptions(
            verbose=False,
            cleanup=False,
            preview=True,
            up=True,
            destroy=True
        )

        directory = Path(__file__)

        cls.t = PulumiIntegrationTest(directory=directory, config=config, plugins=plugins, opts=opts)
        cls.t.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.t.__exit__(None, None, None)

    def setUp(self):
        self.required_tags = {"CreatedBy", "Environment", "BillingProject", "PulumiProject", "PulumiStack"}
        self.ec2 = boto3.client('ec2', region_name=self.region)

    def test_pulumi_preview(self):
        # verify that 9 create steps are planned
        steps = self.t.preview.steps
        self.assertEqual(len(steps), 9)  # includes Step for create ComponentResource:VpcWithPublicSubnets

        for i in steps:
            with self.subTest(msg=f"Verify create step for URN: {i.urn}"):
                self.assertEqual("create", i.op)

    def test_pulumi_up(self):
        resources = self.t.state.resources
        resources.render_tree()

        with self.subTest(msg="Verify resource counts by providers"):
            self.assertEqual(resources.providers["pulumi:providers:aws"], 8)

        table = [
            {
                'type': "aws:ec2/vpc:Vpc",
                'count': 1
            },
            {
                'type': "aws:ec2/subnet:Subnet",
                'count': 2
            },
            {
                'type': "aws:ec2/routeTable:RouteTable",
                'count': 1
            },
            {
                'type': "aws:ec2/internetGateway:InternetGateway",
                'count': 1
            },
            {
                'type': "aws:ec2/routeTableAssociation:RouteTableAssociation",
                'count': 2
            },
            {
                'type': "aws:ec2/route:Route",
                'count': 1
            }
        ]

        for i in table:
            with self.subTest(msg=f"Verify resource count of type: {i['type']}"):
                rtype = resources.types[i["type"]]
                self.assertEqual(rtype, i["count"])

    def test_pulumi_up_idempotency(self):
        # verify that executing `pulumi up` again results in no changes being made
        self.t.up.execute(expect_no_changes=True)

    def test_verify_vpc(self):
        outputs = self.t.get_stack_outputs()

        vpc_id = outputs["vpc"]["id"]

        r   = self.ec2.describe_vpcs(VpcIds=[vpc_id])
        vpc = r["Vpcs"][0]

        with self.subTest(msg="Verify VPC CIDR is correct"):
            self.assertEqual(vpc["CidrBlock"], self.vpc_cidr)

        with self.subTest(msg="Verify tags on the VPC"):
            tags = utils.extract_tags(vpc["Tags"])
            self.assertTrue(self.required_tags <= set(tags))

    def test_verify_subnets(self):
        outputs = self.t.get_stack_outputs()

        # verify that the subnet CIDRs are /20 prefixes
        subnet_ids = [i["id"] for i in outputs["public_subnets"]]
        r = self.ec2.describe_subnets(SubnetIds=subnet_ids)

        expected_cidrs = ["10.0.0.0/20", "10.0.16.0/20"]
        actual_cidrs   = [i["CidrBlock"] for i in r["Subnets"]]
        self.assertListEqual(expected_cidrs, sorted(actual_cidrs))

    def test_verify_route_table(self):
        outputs = self.t.get_stack_outputs()

        vpc_id = outputs["vpc"]["id"]
        rtb_id = outputs["public_route_table"]["id"]

        r   = self.ec2.describe_route_tables(RouteTableIds=[rtb_id])
        rtb = r["RouteTables"][0]

        with self.subTest(msg="Verify route table belongs to the VPC"):
            self.assertEqual(vpc_id, rtb["VpcId"])

        with self.subTest(msg="Verify default route is set correctly"):
            igw_id = outputs["internet_gateway"]["id"]

            self.assertEqual(2, len(rtb["Routes"]))

            default_route = rtb["Routes"][-1]
            self.assertEqual(igw_id, default_route["GatewayId"])
            self.assertEqual("0.0.0.0/0", default_route["DestinationCidrBlock"])

        with self.subTest(msg="Verify tags on the route table"):
            tags = utils.extract_tags(rtb["Tags"])
            self.assertTrue(self.required_tags <= set(tags))
```

Execute the integration test and ensure it passes:

    $ python -m unittest -v test.py

    test_pulumi_preview (examples.aws-vpc.test.IntegrationTest) ... ok
    test_pulumi_up (examples.aws-vpc.test.IntegrationTest) ... ok
    test_pulumi_up_idempotency (examples.aws-vpc.test.IntegrationTest) ... ok
    test_verify_route_table (examples.aws-vpc.test.IntegrationTest) ... ok
    test_verify_subnets (examples.aws-vpc.test.IntegrationTest) ... ok
    test_verify_vpc (examples.aws-vpc.test.IntegrationTest) ... ok

    ----------------------------------------------------------------------
    Ran 6 tests in 39.416s

    OK
