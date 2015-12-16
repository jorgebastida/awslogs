import re
import sys
import os
import time
from threading import Thread, Event
from datetime import datetime, timedelta
from collections import deque
try:
    from Queue import Queue
except ImportError:
    from queue import Queue

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
    MAX_EVENTS_PER_CALL = 10000
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

    def list_logs(self):
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

        queue, exit = Queue(), Event()

        # Note: filter_log_events paginator is broken
        # ! Error during pagination: The same next token was received twice

        def consumer():
            while not exit.is_set():
                event = queue.get()

                if event is None:
                    exit.set()
                    break

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
                print(' '.join(output))

        def generator():
            """Push events into queue trying to deduplicate them using a lru queue.
            AWS API stands for the interleaved parameter that:
                interleaved (boolean) -- If provided, the API will make a best
                effort to provide responses that contain events from multiple
                log streams within the log group interleaved in a single
                response. That makes some responses return some subsequent
                response duplicate events. In a similar way when awslogs is
                called with --watch option, we need to findout which events we
                have alredy put in the queue in order to not do it several
                times while waiting for new ones and reusing the same
                next_token. The site of this queue is MAX_EVENTS_PER_CALL in
                order to not exhaust the memory.
            """
            interleaving_sanity = deque(maxlen=self.MAX_EVENTS_PER_CALL)
            kwargs = {'logGroupName': self.log_group_name,
                      'interleaved': True}

            if streams:
                kwargs['logStreamNames'] = streams

            if self.start:
                kwargs['startTime'] = self.start

            if self.end:
                kwargs['endTime'] = self.end

            while not exit.is_set():
                response = self.client.filter_log_events(**kwargs)

                for event in response.get('events', []):
                    if event['eventId'] not in interleaving_sanity:
                        interleaving_sanity.append(event['eventId'])
                        queue.put(event)

                if 'nextToken' in response:
                    kwargs['nextToken']= response['nextToken']
                else:
                    if self.watch:
                        time.sleep(1)
                    else:
                        queue.put(None)
                        break

        g = Thread(target=generator)
        g.start()

        c = Thread(target=consumer)
        c.start()

        try:
            while not exit.is_set():
                time.sleep(.1)
        except (KeyboardInterrupt, SystemExit):
            exit.set()
            print('Closing...\n')
            os._exit(0)
            

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
                if 'firstEventTimestamp' not in stream:
                    # This is a specified log stream rather than
                    # a filter on the whole log group, so there's
                    #no firstEventTimestamp.
                    yield stream['logStreamName']
                    continue
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

        return int(total_seconds(date - datetime(1970, 1, 1))) * 1000
