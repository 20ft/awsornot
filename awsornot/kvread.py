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

"""A drop in replacement for boto3.session.client - read only client"""

import socket
import json
from botocore.exceptions import ClientError
from . import boto_client, dynamic_data_or_none


class KeyValueRead:
    def __init__(self, port=1026):
        # on aws?
        self.ssm = None
        self.dynamic_data = dynamic_data_or_none()
        if self.dynamic_data is not None:
            self.ssm = boto_client('ssm', self.dynamic_data)
            return

        # not on aws, fetch values with a UDP broadcast
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(1)
        self.socket.bind(('', 0))
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST,1)
        self.socket.sendto(b'', ('<broadcast>', port))
        reply = self.socket.recv(65536)
        self.kvs = json.loads(reply.decode())

    def on_aws(self):
        return self.ssm is not None

    def get_parameter(self, Name):
        if self.ssm is not None:
            return self.ssm.get_parameter(Name=Name)
        else:
            try:
                return {'Parameter': {'Value': self.kvs[Name]}}
            except KeyError:
                raise ClientError(operation_name='get_parameter',
                                  error_response={'ResponseMetadata': {'MaxAttemptsReached': True}})
