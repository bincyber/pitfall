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

# Provision an AWS S3 Bucket
bucket = aws.s3.Bucket(resource_name=bucket_name, force_destroy=True, tags=tags)

# Export the name of the S3 bucket
pulumi.export('s3_bucket_name', bucket.id)
