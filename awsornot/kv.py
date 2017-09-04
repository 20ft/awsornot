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


import cbor
import os
import os.path
import logging
from bottle import Bottle, run
from threading import Thread
from . import dynamic_data_or_none, boto_client
from botocore.exceptions import ClientError


kvserve = Bottle()


class KeyValue(Thread):  # thread is for the server (that won't be run under AWS)
    fname = None
    port = None
    ssm = None
    dynamic_data = None

    def __init__(self, non_aws_filename="kvstore", port=1026, *, noserver=False):
        super().__init__(target=KeyValue._serve, name=str("KVStore"), daemon=True)
        # Self.ssm gets created if we are under AWS
        os.makedirs(os.path.basename(non_aws_filename), exist_ok=True)
        KeyValue.fname = non_aws_filename
        KeyValue.port = port
        KeyValue.dynamic_data = dynamic_data_or_none()
        if KeyValue.dynamic_data is not None:
            KeyValue.ssm = boto_client('ssm', self.dynamic_data)
        else:
            if not noserver:
                self.start()  # the thread for the kv server

    def stop(self):
        if KeyValue.dynamic_data is None:  # only if we're running the KV server
            kvserve.close()

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
            with open(KeyValue.fname, "w+b") as f:
                f.write(cbor.dumps(values))

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
            with open(KeyValue.fname, "r+b") as f:
                return cbor.loads(f.read())
        except FileNotFoundError:
            return {}

    # serving the values with bottle
    @staticmethod
    def _serve():
        try:
            logging.info("Started KV server: 0.0.0.0:" + str(KeyValue.port))
            run(app=kvserve, host='0.0.0.0', port=KeyValue.port, quiet=True)
        except OSError:
            logging.critical("Could not bind KV server, exiting")
            exit(1)

    @staticmethod
    @kvserve.route('/')
    def _state():
        with open(KeyValue.fname, "r+b") as f:
            return f.read()

