import re
import time
from functools import partial
from datetime import datetime, timedelta

import boto
import gevent
from termcolor import colored
from boto import logs as botologs
from dateutil.parser import parse

import exceptions


class AWSConnection(object):
    """Wrapper on top of boto's ``connect_to_region`` which retry api
    calls if some well-known errors occur."""

    def __init__(self, *args, **kwargs):
        self.connection = botologs.connect_to_region(*args, **kwargs)
        if not self.connection:
            raise exceptions.ConnectionError()

    def __bool__(self):
        return bool(self.connection)

    def __getattr__(self, name):

        def aws_connection_wrap(*args, **kwargs):
            while True:
                try:
                    return getattr(self.connection, name)(*args, **kwargs)
                except boto.exception.JSONResponseError, exc:
                    if exc.error_code == u'ThrottlingException':
                        gevent.sleep(0.5)

        return aws_connection_wrap


class AWSLogs(object):

    def __init__(self, **kwargs):
        self.aws_region = kwargs.get('aws_region')
        self.aws_access_key_id = kwargs.get('aws_access_key_id')
        self.aws_secret_access_key = kwargs.get('aws_secret_access_key')
        self.log_group_name = kwargs.get('log_group_name')
        self.log_stream_name = kwargs.get('log_stream_name')
        self.watch = kwargs.get('watch')
        self.color_enabled = kwargs.get('color_enabled')
        self.output_stream_enabled = kwargs.get('output_stream_enabled')
        self.output_group_enabled = kwargs.get('output_group_enabled')
        self.start = self.parse_datetime(kwargs.get('start'))
        self.end = self.parse_datetime(kwargs.get('end'))
        self.pool_size = kwargs.get('pool_size', 20)
        self.max_group_length = 0
        self.max_stream_length = 0
        self.connection = AWSConnection(self.aws_region,
                                        aws_access_key_id=self.aws_access_key_id,
                                        aws_secret_access_key=self.aws_secret_access_key)

    def _get_streams_from_patterns(self, log_group_pattern, log_stream_pattern):
        """Returns pairs of group, stream matching ``log_group_pattern`` and
        ``log_stream_pattern``."""
        for group in self._get_groups_from_pattern(log_group_pattern):
            for stream in self._get_streams_from_pattern(group, log_stream_pattern):
                yield group, stream

    def _get_groups_from_pattern(self, pattern):
        """Returns groups matching ``pattern``."""
        reg = re.compile('^{0}'.format(pattern))
        for group in self.get_groups():
            if pattern == '*' or re.match(reg, group):
                yield group

    def _get_streams_from_pattern(self, group, pattern):
        """Returns streams in ``group`` matching ``pattern``."""
        reg = re.compile('^{0}'.format(pattern))
        for stream in self.get_streams(group):
            if pattern == '*' or re.match(reg, stream):
                yield stream

    def _get_stream_logs(self, log_group_name, log_stream_name):
        """Returns events in ``log_stream_name`` of ``log_group_name``."""

        next_token = None
        while True:
            response = self.connection.get_log_events(next_token=next_token,
                                                      log_group_name=log_group_name,
                                                      log_stream_name=log_stream_name,
                                                      start_time=self.start,
                                                      end_time=self.end)

            active = False
            for event in response['events']:
                active = True
                event['group'] = log_group_name
                event['stream'] = log_stream_name
                yield event

            if 'nextForwardToken' in response:
                next_token = response['nextForwardToken']
            else:
                break

            if not active:
                yield None

    def get_logs(self):
        """Returns events for streams matching ``log_group_name`` in groups
        matching ``log_group_name``."""
        sources = []

        for group, stream in self._get_streams_from_patterns(self.log_group_name, self.log_stream_name):
            self.max_group_length = max(self.max_group_length, len(group))
            self.max_stream_length = max(self.max_stream_length, len(stream))
            sources.append(self._get_stream_logs(group, stream))

        first, values = True, []

        while first or any(values) or self.watch:
            earliests = sorted((v for v in values if v), key=lambda x: x['timestamp'])

            if earliests:
                earliest = earliests[0]
            else:
                if not first:
                    time.sleep(1)
                first = False

                # Asyncronously get the first page of all streams
                pool = gevent.pool.Pool(self.pool_size)
                greens = []
                for source in sources:
                    greens.append(pool.spawn(source.next))
                pool.join()
                values = [g.value for g in greens]
                continue

            index = values.index(earliest)
            try:
                values[index] = sources[index].next()
            except StopIteration:
                values[index] = None
            yield earliest

    def list_logs(self):
        """Lists available CloudWatch logs groups"""
        for line in self.get_logs():
            output = [line['message']]
            if self.output_stream_enabled:
                output.insert(0, self.color(line['stream'].ljust(self.max_stream_length, ' '), 'cyan'))
            if self.output_group_enabled:
                output.insert(0, self.color(line['group'].ljust(self.max_group_length, ' '), 'green'))
            print ' '.join(output)

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
        next_token = None
        while True:
            response = self.connection.describe_log_groups(next_token=next_token)
            for group in response.get('logGroups', []):
                yield group['logGroupName']

            if 'nextToken' in response:
                next_token = response['nextToken']
            else:
                break

    def get_streams(self, log_group_name=None):
        """Returns available CloudWatch logs streams in ``log_group_name``."""
        log_group_name = log_group_name or self.log_group_name
        next_token = None

        while True:
            response = self.connection.describe_log_streams(log_group_name=self.log_group_name, next_token=next_token)

            for stream in response.get('logStreams', []):
                yield stream['logStreamName']

            if 'nextToken' in response:
                next_token = response['nextToken']
            else:
                break

    def color(self, text, color):
        """Returns coloured version of ``text`` if ``color_enabled``."""
        if self.color_enabled:
            return colored(text, color)
        return text

    def parse_datetime(self, datetime_text):
        if not datetime_text:
            return None

        ago_match = re.match(r'(\d+)\s?(m|minutes|minute|d|day|days|h|hour|hours|w|weeks|weeks)(?: ago)?', datetime_text)
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
