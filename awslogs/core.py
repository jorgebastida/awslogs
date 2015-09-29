import re
import sys
import time
from datetime import datetime, timedelta

import boto3
from botocore.compat import total_seconds
from botocore.client import ClientError
from botocore.auth import NoCredentialsError
from botocore.retryhandler import EndpointConnectionError

from termcolor import colored
from dateutil.parser import parse

from . import exceptions

__version__ = '0.1.0'


class AWSLogs(object):

    ACTIVE = 1
    EXHAUSTED = 2
    WATCH_SLEEP = 2

    FILTER_LOG_EVENTS_STREAMS_LIMIT = 100
    ALL_WILDCARD = 'ALL'

    def __init__(self, **kwargs):
        self.aws_region = kwargs.get('aws_region')
        self.aws_access_key_id = kwargs.get('aws_access_key_id')
        self.aws_secret_access_key = kwargs.get('aws_secret_access_key')
        self.aws_session_token = kwargs.get('aws_session_token')
        self.log_group_name = kwargs.get('log_group_name')
        self.log_stream_name = kwargs.get('log_stream_name')
        self.watch = kwargs.get('watch')
        self.color_enabled = kwargs.get('color_enabled')
        self.output_stream_enabled = kwargs.get('output_stream_enabled')
        self.output_group_enabled = kwargs.get('output_group_enabled')
        self.start = self.parse_datetime(kwargs.get('start'))
        self.end = self.parse_datetime(kwargs.get('end'))

        self.client = boto3.client('logs',
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            aws_session_token=self.aws_session_token,
            region_name=self.aws_region
        )

    def _get_streams_from_pattern(self, group, pattern):
        """Returns streams in ``group`` matching ``pattern``."""
        pattern = '.*' if pattern == self.ALL_WILDCARD else pattern
        reg = re.compile('^{0}'.format(pattern))
        for stream in self.get_streams(group):
            if re.match(reg, stream):
                yield stream

    def get_logs(self):

        streams = []
        if self.log_stream_name != self.ALL_WILDCARD:
            streams = list(self._get_streams_from_pattern(self.log_group_name, self.log_stream_name))
            if len(streams) > self.FILTER_LOG_EVENTS_STREAMS_LIMIT:
                raise exceptions.TooManyStreamsFilteredError(
                     self.log_stream_name,
                     len(streams),
                     self.FILTER_LOG_EVENTS_STREAMS_LIMIT
                )

        max_stream_length = max([len(s) for s in streams]) if streams else 10
        group_length = len(self.log_group_name)

        kwargs = {'logGroupName': self.log_group_name,
                  'interleaved': True}

        if streams:
            kwargs['logStreamNames'] = streams

        if self.start:
            kwargs['startTime'] = self.start

        if self.end:
            kwargs['endTime'] = self.end

        # Note: filter_log_events paginator is broken
        # Error during pagination: The same next token was received twice
        #paginator = self.client.get_paginator('filter_log_events')
        #for page in paginator.paginate(**kwargs):
        #    for event in page.get('events', []):

        while True:
            response = self.client.filter_log_events(**kwargs)
            for event in response.get('events', []):
                output = [event['message']]
                if self.output_stream_enabled:
                    output.insert(
                        0,
                        self.color(
                            event['logStreamName'].ljust(max_stream_length, ' '),
                            'cyan'
                        )
                    )
                if self.output_group_enabled:
                    output.insert(
                        0,
                        self.color(
                             self.log_group_name.ljust(group_length, ' '),
                            'green'
                        )
                    )
                yield ' '.join(output)

            if 'nextToken' in response:
                kwargs['nextToken']= response['nextToken']
            else:
                break

    def list_logs(self):
        for event in self.get_logs():
            print(event)

    def list_groups(self):
        """Lists available CloudWatch logs groups"""
        for group in self.get_groups():
            print(group)

    def list_streams(self):
        """Lists available CloudWatch logs streams in ``log_group_name``."""
        for stream in self.get_streams():
            print(stream)

    def get_groups(self):
        """Returns available CloudWatch logs groups"""
        paginator = self.client.get_paginator('describe_log_groups')
        for page in paginator.paginate():
            for group in page.get('logGroups', []):
                yield group['logGroupName']

    def get_streams(self, log_group_name=None):
        """Returns available CloudWatch logs streams in ``log_group_name``."""
        kwargs = {'logGroupName': log_group_name or self.log_group_name}
        window_start = self.start or 0
        window_end = self.end or sys.maxsize

        paginator = self.client.get_paginator('describe_log_streams')
        for page in paginator.paginate(**kwargs):
            for stream in page.get('logStreams', []):
                if max(stream['firstEventTimestamp'], window_start) <= \
                   min(stream['lastEventTimestamp'], window_end):
                    yield stream['logStreamName']

    def color(self, text, color):
        """Returns coloured version of ``text`` if ``color_enabled``."""
        if self.color_enabled:
            return colored(text, color)
        return text

    def parse_datetime(self, datetime_text):
        """Parse ``datetime_text`` into a ``datetime``."""

        if not datetime_text:
            return None

        ago_match = re.match(r'(\d+)\s?(m|minute|minutes|h|hour|hours|d|day|days|w|weeks|weeks)(?: ago)?', datetime_text)
        if ago_match:
            amount, unit = ago_match.groups()
            amount = int(amount)
            unit = {'m': 60, 'h': 3600, 'd': 86400, 'w': 604800}[unit[0]]
            date = datetime.utcnow() + timedelta(seconds=unit * amount * -1)
        else:
            try:
                date = parse(datetime_text)
            except ValueError:
                raise exceptions.UnknownDateError(datetime_text)

        return int(total_seconds(date - datetime(1970, 1, 1)) * 1000)
