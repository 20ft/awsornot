# Copyright (c) 2017 David Preece, All rights reserved.
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
"""Various utilities"""

import json
import cbor
import requests
import boto3
from botocore.exceptions import ClientError

dd_result_cache = None
dd_have_result = False


def dynamic_data_or_none():
    """Returns the instance identity document on AWS or None"""
    global dd_result_cache, dd_have_result
    if not dd_have_result:
        try:
            dynamic_data_text = requests.get('http://169.254.169.254/latest/dynamic/instance-identity/document',
                                             timeout=0.5).text
            dd_result_cache = json.loads(dynamic_data_text)
        except requests.exceptions.ConnectionError:
            dd_result_cache = None
        dd_have_result = True
    return dd_result_cache


def boto_client(type, dynamic_data):
    """Create a boto client. Type is efs, ssm etc."""
    session = boto3.session.Session(region_name=dynamic_data['region'])
    try:
        return session.client(type)
    except ClientError:
        raise RuntimeError("There was a problem creating a client for '%s'\n" +
                           "Please ensure you are running under a profile with the correct permissions.")
