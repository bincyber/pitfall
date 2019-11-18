# Copyright 2019 Ali (@bincyber)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import List, Dict, Any


def extract_tags(tag_set: List[Dict[str, Any]]) -> dict:
    """
    Returns a dictionary containing the keys and values extracted from an AWS tag set.

    :param tag_set: a list of Tag objects, eg. [{'Key': 'Name', 'Value': 'test'}]
    :type tag_set: list

    :returns: a dictionary of Tag key/value pairs
    :rtype: dict
    """
    tags = {}
    for i in tag_set:
        k = i["Key"]
        v = i["Value"]
        tags[k] = v
    return tags
