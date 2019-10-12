from datetime import datetime
import pulumi_aws as aws
import pulumi


cfg = pulumi.Config()

bucket_name = cfg.require("s3-bucket-name")

creation_date = datetime.utcnow().strftime('%Y/%m/%d')

tags = {
    'Environment': cfg.require('environment'),
    'BillingProject': cfg.require('billing-project'),
    'CreatedBy': 'Pulumi',
    'CreatedOn': creation_date,
    'Owner': cfg.require('owner'),
    'PulumiProject': pulumi.get_project(),
    'PulumiStack': pulumi.get_stack(),
    'Customer': cfg.require_secret('customer')
}

opts = pulumi.ResourceOptions()

if cfg.get_bool("local-mode"):
    opts.provider = aws.Provider(
        resource_name="localstack",
        access_key="integration-testing",
        secret_key="integration-testing",
        region="us-east-1",
        endpoints=[{"s3": "http://localhost:4572"}],
        skip_credentials_validation=True,
        s3_force_path_style=True,
        skip_metadata_api_check=True,
        skip_requesting_account_id=True,
        skip_region_validation=True
    )

# Provision an AWS S3 Bucket
bucket = aws.s3.Bucket(resource_name=bucket_name, force_destroy=False, tags=tags, opts=opts)

# Export the name of the S3 bucket
pulumi.export('s3_bucket_name', bucket.id)
