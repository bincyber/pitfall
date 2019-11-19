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
