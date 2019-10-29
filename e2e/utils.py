

def extract_tags_from_aws_resource(resource: dict) -> dict:
    """ extracts tags from the response body for an AWS resource """
    tags = {}
    for i in resource["Tags"]:
        k = i["Key"]
        v = i["Value"]
        tags[k] = v
    return tags
