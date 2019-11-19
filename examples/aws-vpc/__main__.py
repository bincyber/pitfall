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
