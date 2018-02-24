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

"""AWS CloudWatch compatible logger - logs to stdout if not running under AWS"""

import json.decoder
import requests
import boto3
import logging
import json
import time
import signal
import os
import botocore.errorfactory
from botocore.exceptions import ClientError, EndpointConnectionError
from threading import Thread
from queue import Queue


class LogHandler(logging.Handler):
    def __init__(self, group, stream, blacklist=None):
        try:
            # see if we are logging verbosely
            dynamic_data_text = requests.get('http://169.254.169.254/latest/dynamic/instance-identity/document').text
            ssm = boto3.client('ssm', region_name=json.loads(dynamic_data_text)['region'])
            try:
                verbose_string = ssm.get_parameter(Name='/20ft/verbose')['Parameter']['Value']
            except ClientError:  # string not written yet
                verbose_string = 'False'
            level = logging.DEBUG if verbose_string == 'True' or verbose_string == 'true' else logging.INFO

            # find instance ID
            iid = requests.get('http://169.254.169.254/latest/meta-data/instance-id').text
            stream_name = stream + '/' + iid

        except requests.exceptions.ConnectionError:  # not running under AWS
            level = logging.INFO
            stream_name = None

        super().__init__(level)
        self.blacklist = blacklist if blacklist is not None else []
        self.formatter = logging.Formatter(fmt='%(levelname)-8s %(message)s')
        logging.basicConfig(level=level, handlers=[self])

        # delivery thread (aws only)
        self.queue = None
        if stream_name is not None:
            self.queue = Queue()
            self.thread = Thread(target=self.background, args=(group, stream_name, self.queue))
            self.thread.start()

    def emit(self, record):
        # urllib and boto try to log themselves doing all sorts
        if record.name.startswith('urllib3') or record.name.startswith('botocore'):
            return

        # is the log on the blacklist?
        text = self.formatter.format(record)
        for string in self.blacklist:
            if string in text:
                return

        # otherwise enqueue the record
        print(self.formatter.format(record))
        if self.queue is not None:
            self.queue.put(record)

    def stop(self):
        """Posts a message on the queue telling the logging thread to stop."""
        if self.queue is not None:
            self.queue.put(None)

    def background(self, group, stream, queue):
        """Runs as a background thread delivering the logs as they arrive (to avoid stalling the event loop)"""
        # create a cloud watch log client
        dynamic_data_text = requests.get('http://169.254.169.254/latest/dynamic/instance-identity/document').text
        aws_logger = boto3.client('logs', region_name=json.loads(dynamic_data_text)['region'])

        # create the group and stream if need be
        groups = aws_logger.describe_log_groups(
            logGroupNamePrefix=group
        )['logGroups']
        groups_dict = {g['logGroupName']: g for g in groups}
        if group not in groups_dict.keys():
            aws_logger.create_log_group(
                    logGroupName=group
            )
        stream_desc = aws_logger.describe_log_streams(
                logGroupName=group,
                logStreamNamePrefix=stream
        )
        sequence_token = '0'
        streams = {s['logStreamName']: s for s in stream_desc['logStreams']}
        if stream not in streams:
            aws_logger.create_log_stream(
                    logGroupName=group,
                    logStreamName=stream
            )
        else:
            sequence_token = streams[stream]['uploadSequenceToken']

        # loop picking logs off the queue and delivering
        while True:
            record = queue.get()
            if record is None:
                return
            text = self.formatter.format(record)
            sent = False
            while not sent:
                try:
                    result = aws_logger.put_log_events(
                            logGroupName=group,
                            logStreamName=stream,
                            logEvents=[
                                {
                                    'timestamp': int(record.created * 1000),
                                    'message': text
                                }
                            ],
                            sequenceToken=sequence_token
                    )
                    sequence_token = result['nextSequenceToken']
                    sent = True
                except ClientError as e:
                    print("....LogHandler error: " + str(e))
                    time.sleep(2)
                except EndpointConnectionError:
                    print("...Name resolution has failed")
                    self.queue.put(None)
                except BaseException as e:
                    print("...A bad thing happened with the logging thread: " + str(e))
                    return
