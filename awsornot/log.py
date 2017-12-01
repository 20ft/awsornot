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
from botocore.exceptions import ClientError, EndpointConnectionError
from multiprocessing import Queue, Process


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

        # delivery process (aws only)
        self.queue = None
        if stream_name is not None:
            self.queue = Queue()
            self.process = Process(target=self.background, args=(group, stream_name, self.queue))
            self.process.start()

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
        """Posts a message on the queue telling the logging process to stop."""
        if self.queue is not None:
            self.queue.put(None)

    def background(self, group, stream, queue):
        """Runs as a background process delivering the logs as they arrive (to avoid stalling the event loop)"""
        # ignore KeyboardInterrupt because we want to log as we close down
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        # create a cloud watch log client
        sequence_token = None
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
        streams = aws_logger.describe_log_streams(
                logGroupName=group,
                logStreamNamePrefix=stream
        )['logStreams']
        streams_dict = {s['logStreamName']: s for s in streams}
        if stream not in streams_dict.keys():
            result = aws_logger.create_log_stream(
                    logGroupName=group,
                    logStreamName=stream
            )
        else:
            try:
                sequence_token = streams_dict[stream]['uploadSequenceToken']
            except KeyError:
                pass

        # loop picking logs off the queue and delivering
        while True:
            record = queue.get()
            if record is None:
                return
            text = self.formatter.format(record)

            # No, seriously, you have to do this :(
            result = None
            if sequence_token is None:
                result = aws_logger.put_log_events(
                        logGroupName=group,
                        logStreamName=stream,
                        logEvents=[
                            {
                                'timestamp': int(record.created * 1000),
                                'message': text
                            }
                        ]  # you can't pass None as the sequence token
                )
            else:
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
                        sent = True
                    except ClientError:
                        print("....LogHandler told to back off by AWS.")
                        time.sleep(2)
                    except EndpointConnectionError:
                        print("...Name resolution has failed")
                        self.queue.put(None)
                sequence_token = result['nextSequenceToken']
