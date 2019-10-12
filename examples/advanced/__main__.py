from json import dumps
from pathlib import Path
import pulumi_aws as aws
import pulumi


def get_json_bucket_policy(bucket_arn):
    return dumps({
    "Version": "2012-10-17",
    "Statement": [{
        "Sid": "PublicReadGetObject",
        "Effect": "Allow",
        "Principal": "*",
        "Action": ["s3:GetObject"],
        "Resource": f"{bucket_arn}/*"
    }]
})

cfg = pulumi.Config()

bucket_name = cfg.require("s3-bucket-name")

tags = {
    'CreatedBy': 'Pulumi',
    'PulumiProject': pulumi.get_project(),
    'PulumiStack': pulumi.get_stack(),
}

bucket = aws.s3.Bucket(
    resource_name=bucket_name,
    force_destroy=True,
    tags=tags,
    acl="public-read",
    website={
        "index_document":"index.html"
    }
)

policy = bucket.arn.apply(get_json_bucket_policy)

bucket_policy = aws.s3.BucketPolicy(
    resource_name="public_read_get_object",
    bucket=bucket.id,
    policy=policy
)

index_file = Path('./index.html')

bucket_object = aws.s3.BucketObject(
    resource_name="index.html",
    acl="public-read",
    bucket=bucket.id,
    key="index.html",
    content=index_file.read_text(),
    content_type="text/html"
)

url = pulumi.Output.concat("http://", bucket.website_endpoint)

pulumi.export('bucket_name', bucket.id)
pulumi.export('website_url', url)
