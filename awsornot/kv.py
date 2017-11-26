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
"""A drop in replacement for boto3.session.client"""


import json
import socketserver
import _thread
import logging
import os
from . import dynamic_data_or_none, boto_client
from botocore.exceptions import ClientError


class KeyValue:
    fname = None

    def __init__(self, non_aws_filename="kvstore", port=1026, *, noserver=False):
        # Self.ssm gets created if we are under AWS
        KeyValue.fname = non_aws_filename
        self.dynamic_data = dynamic_data_or_none()
        self.ssm = None
        self.server = None
        if self.is_aws():
            self.ssm = boto_client('ssm', self.dynamic_data)
        else:
            if '/' in non_aws_filename:  # at least *a* directory
                last_slash = non_aws_filename.rfind('/')
                os.makedirs(non_aws_filename[:last_slash], exist_ok=True)
            if not noserver:
                self.server = socketserver.UDPServer(('0.0.0.0', port), KeyValue._UDPHandler)
                _thread.start_new_thread(socketserver.UDPServer.serve_forever, (self.server,))

    def stop(self):
        if self.server is not None:
            self.server.shutdown()
            
    def is_aws(self):
        return self.dynamic_data is not None

    # non pep8 names are to retain compatibility with the AWS calls
    def put_parameter(self, Name, Description, Type, Value, Overwrite):
        if self.ssm:
            self.ssm.put_parameter(Name=Name, Description=Description, Type=Type, Value=Value, Overwrite=Overwrite)
        else:
            # write into a file just called "kvstore". create if not there
            values = KeyValue._values()
            if Name in values.keys() and not Overwrite:
                raise ValueError("Tried to overwrite a kv parameter with Overwrite=False")
            values[Name] = Value
            json_string = json.dumps(values, indent=2)
            if len(json_string) > 65536:
                raise RuntimeError("Cannot write parameter, KV storage total allocation is 64K")
            with open(KeyValue.fname, "w") as f:
                f.write(json_string)

    # ditto, retaining compatibility
    def get_parameter(self, Name):
        if self.ssm:
            return self.ssm.get_parameter(Name=Name)
        else:
            values = KeyValue._values()
            try:
                return {'Parameter': {'Value': values[Name]}}
            except KeyError:
                raise ClientError(operation_name='get_parameter',
                                  error_response={'ResponseMetadata': {'MaxAttemptsReached': True}})

    @staticmethod
    def _values():
        try:
            with open(KeyValue.fname, "r") as f:
                return json.loads(f.read())
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            return {}

    class _UDPHandler(socketserver.BaseRequestHandler):
        def handle(self):
            skt = self.request[1]
            try:
                with open(KeyValue.fname, "r") as f:
                    skt.sendto(f.read().encode(), self.client_address)
                logging.debug("Served kv store to: " + str(self.client_address))
            except FileNotFoundError:
                return skt.sendto("{}", self.client_address)
