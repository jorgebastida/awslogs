import re
import sys
import time
from datetime import datetime, timedelta

import boto3

from termcolor import colored
from boto import logs as botologs
from dateutil.parser import parse

import exceptions

__version__ = '0.1.0'

#NO_MORE_EVENTS = object()

#
# class AWSConnection(object):
#     """Wrapper on top of boto's ``connect_to_region`` which retry api
#     calls if some well-known errors occur."""
#
#     def __init__(self, aws_region, *args, **kwargs):
#
#         if aws_region not in (r.name for r in botologs.regions()):
#             raise exceptions.InvalidRegionError(aws_region)
#
#         try:
#             self.connection = botologs.connect_to_region(aws_region, *args, **kwargs)
#         except boto.exception.NoAuthHandlerFound, exc:
#             raise exceptions.NoAuthHandlerFoundError(*exc.args)
#
#         if not self.connection:
#             raise exceptions.ConnectionError()
#
#     def __bool__(self):
#         return bool(self.connection)
#
#     def __getattr__(self, name):
#
#         def aws_connection_wrap(*args, **kwargs):
#             while True:
#                 try:
#                     return getattr(self.connection, name)(*args, **kwargs)
#                 except boto.exception.JSONResponseError, exc:
#                     if exc.error_code == u'ThrottlingException':
#                         gevent.sleep(1)
#                         continue
#                     elif exc.error_code == u'AccessDeniedException':
#                         hint = exc.body.get('Message', 'AccessDeniedException')
#                         raise exceptions.AccessDeniedError(hint)
#                     raise
#                 except Exception, exc:
#                     raise
#
#         return aws_connection_wrap


class AWSLogs(object):

    ACTIVE = 1
    EXHAUSTED = 2
    WATCH_SLEEP = 2

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
        pattern = '.*' if pattern == 'ALL' else pattern
        reg = re.compile('^{0}'.format(pattern))
        for stream in self.get_streams(group):
            if re.match(reg, stream):
                yield stream

    def get_logs(self):
        streams = list(self._get_streams_from_pattern(self.log_group_name, self.log_stream_name))
        max_stream_length = max([len(s) for s in streams])
        group_length = len(self.log_group_name)

        kwargs = {'logGroupName': self.log_group_name,
                  'logStreamNames': streams,
                  'interleaved': True}
        if self.start:
            kwargs['startTime'] = self.start

        if self.end:
            kwargs['endTime'] = self.end

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
            print event

    def list_groups(self):
        """Lists available CloudWatch logs groups"""
        for group in self.get_groups():
            print group

    def list_streams(self, *args, **kwargs):
        """Lists available CloudWatch logs streams in ``log_group_name``."""
        for stream in self.get_streams(*args, **kwargs):
            print stream

    def get_groups(self):
        """Returns available CloudWatch logs groups"""
        kwargs = {}
        while True:
            response = self.client.describe_log_groups(**kwargs)

            for group in response.get('logGroups', []):
                yield group['logGroupName']

            if 'nextToken' in response:
                kwargs['nextToken']= response['nextToken']
            else:
                break

    def get_streams(self, log_group_name=None):
        """Returns available CloudWatch logs streams in ``log_group_name``."""
        kwargs = {'logGroupName': log_group_name or self.log_group_name}
        window_start = self.start or 0
        window_end = self.end or sys.maxint

        while True:
            response = self.client.describe_log_streams(**kwargs)
            for stream in response.get('logStreams', []):
                if max(stream['firstEventTimestamp'], window_start) <= \
                   min(stream['lastEventTimestamp'], window_end):
                    yield stream['logStreamName']

            if 'nextToken' in response:
                kwargs['nextToken'] = response['nextToken']
            else:
                break

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
            date = datetime.now() + timedelta(seconds=unit * amount * -1)
        else:
            try:
                date = parse(datetime_text)
            except ValueError:
                raise exceptions.UnknownDateError(datetime_text)

        return int(date.strftime("%s")) * 1000
