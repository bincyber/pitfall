from netaddr import IPNetwork
from typing import List
import pulumi_aws as aws
import pulumi


class VpcWithPublicSubnets(pulumi.ComponentResource):
    def __init__(self, name: str, cidr: str, subnets: int = 2, prefix: int = 19, tags: dict = None, opts: pulumi.ResourceOptions = None):
        super().__init__('ComponentResource:VpcWithPublicSubnets', name, None, opts)

        self.vpc_name = name
        self.cidr     = cidr
        self.subnets  = subnets
        self.prefix   = prefix
        self.tags     = {} if tags is None else tags

        self.availability_zones = aws.get_availability_zones().names

        self.provision_resources()

        # signal to Pulumi that we are done creating resources
        self.register_outputs({})

    def get_subnets_cidrs(self, cidr: str, count: int, prefix: int) -> list:
        network = IPNetwork(cidr)
        subnets = list(network.subnet(prefix))[:count]
        return subnets[:count]

    def provision_resources(self):
        self._vpc                = self.create_vpc()
        self._internet_gateway   = self.create_internet_gateway()
        self._public_subnets     = self.create_public_subnets()
        self._public_route_table = self.create_public_route_table()

        self.create_public_default_route()
        self.create_public_route_table_association()

    def create_vpc(self) -> aws.ec2.Vpc:
        return aws.ec2.Vpc(
            "vpc",
            cidr_block=self.cidr,
            enable_dns_hostnames=True,
            enable_dns_support=True,
            tags={
                "Name": self.vpc_name,
                **self.tags
            },
            opts=pulumi.ResourceOptions(parent=self)
        )

    def create_internet_gateway(self) -> aws.ec2.InternetGateway:
        return aws.ec2.InternetGateway(
            "internet-gateway",
            vpc_id=self._vpc.id,
            tags={
                "Name": self.vpc_name,
                **self.tags
            },
            opts=pulumi.ResourceOptions(parent=self)
        )

    def create_public_subnets(self) -> List[aws.ec2.Subnet]:
        cidrs = self.get_subnets_cidrs(self.cidr, self.subnets, self.prefix)

        subnets = []

        for i, cidr in enumerate(cidrs):
            name = f"public-subnet-{i + 1}"

            subnet = aws.ec2.Subnet(
                name,
                vpc_id=self.vpc.id,
                cidr_block=str(cidr),
                availability_zone=self.availability_zones[i],
                map_public_ip_on_launch=True,
                assign_ipv6_address_on_creation=False,
                tags={
                    "Name": name,
                    "VPC": self.vpc.id,
                    **self.tags
                },
                opts=pulumi.ResourceOptions(parent=self)
            )
            subnets.append(subnet)
        return subnets

    def create_public_route_table(self) -> aws.ec2.RouteTable:
        name = "public-route-table"

        return aws.ec2.RouteTable(
            name,
            vpc_id=self._vpc.id,
            tags={
                "Name": name,
                **self.tags
            },
            opts=pulumi.ResourceOptions(parent=self)
        )

    def create_public_default_route(self) -> aws.ec2.Route:
        return aws.ec2.Route(
            "public-default-gw",
            route_table_id=self.public_route_table.id,
            destination_cidr_block="0.0.0.0/0",
            gateway_id=self.internet_gateway.id,
            opts=pulumi.ResourceOptions(parent=self)
        )

    def create_public_route_table_association(self) -> None:
        for i, subnet in enumerate(self.public_subnets):
            aws.ec2.RouteTableAssociation(
                f"public-subnet-{i + 1}-rta",
                subnet_id=subnet.id,
                route_table_id=self.public_route_table.id,
                opts=pulumi.ResourceOptions(parent=self)
            )

    @property
    def vpc(self) -> aws.ec2.Vpc:
        return self._vpc

    @property
    def internet_gateway(self) -> aws.ec2.InternetGateway:
        return self._internet_gateway

    @property
    def public_subnets(self) -> List[aws.ec2.Subnet]:
        return self._public_subnets

    @property
    def public_route_table(self) -> aws.ec2.RouteTable:
        return self._public_route_table

    def export(self):
        pulumi.export("vpc", self.vpc)
        pulumi.export("internet_gateway", self.internet_gateway)
        pulumi.export("public_subnets", self.public_subnets)
        pulumi.export("public_route_table", self.public_route_table)
