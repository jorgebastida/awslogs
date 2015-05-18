import re
import sys
import time
from datetime import datetime, timedelta

import boto
import gevent
from gevent.queue import PriorityQueue, Empty, Queue
from gevent.pool import Pool, Group

from termcolor import colored
from boto import logs as botologs
from dateutil.parser import parse

import exceptions

__version__ = '0.0.1'

NO_MORE_EVENTS = object()


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
                        gevent.sleep(1)
                        continue
                    raise
                except Exception, exc:
                    raise

        return aws_connection_wrap


class AWSLogs(object):

    ACTIVE = 1
    EXHAUSTED = 2
    WATCH_SLEEP = 2

    def __init__(self, **kwargs):
        self.connection_cls = kwargs.get('connection_cls', AWSConnection)
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
        self.pool_size = max(kwargs.get('pool_size', 0), 10)
        self.max_group_length = 0
        self.max_stream_length = 0
        self.publishers = []
        self.events_queue = Queue()
        self.raw_events_queue = PriorityQueue()
        self.publishers_queue = PriorityQueue()
        self.publishers = []
        self.stream_status = {}
        self.stream_max_timestamp = {}
        self.connection = self.connection_cls(
            self.aws_region,
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key
        )

    def _get_streams_from_patterns(self, log_group_pattern, log_stream_pattern):
        """Returns pairs of group, stream matching ``log_group_pattern`` and
        ``log_stream_pattern``."""
        for group in self._get_groups_from_pattern(log_group_pattern):
            for stream in self._get_streams_from_pattern(group,
                                                         log_stream_pattern):
                yield group, stream

    def _get_groups_from_pattern(self, pattern):
        """Returns groups matching ``pattern``."""
        pattern = '.*' if pattern == 'ALL' else pattern
        reg = re.compile('^{0}'.format(pattern))
        for group in self.get_groups():
            if re.match(reg, group):
                yield group

    def _get_streams_from_pattern(self, group, pattern):
        """Returns streams in ``group`` matching ``pattern``."""
        pattern = '.*' if pattern == 'ALL' else pattern
        reg = re.compile('^{0}'.format(pattern))
        for stream in self.get_streams(group):
            if re.match(reg, stream):
                yield stream

    def _publisher_queue_consumer(self):
        """Consume ``publishers_queue`` api calls, run them and publish log
        events to ``raw_events_queue``. If ``nextForwardToken`` is present
        register a new api call into ``publishers_queue`` using as weight
        the timestamp of the latest event."""
        while True:
            try:
                _, (log_group_name, log_stream_name, next_token) = self.publishers_queue.get(block=False)
            except Empty:
                if self.watch:
                    gevent.sleep(self.WATCH_SLEEP)
                else:
                    break

            response = self.connection.get_log_events(
                next_token=next_token,
                log_group_name=log_group_name,
                log_stream_name=log_stream_name,
                start_time=self.start,
                end_time=self.end,
                start_from_head=True
            )

            if not len(response['events']):
                self.stream_status[(log_group_name, log_stream_name)] = self.EXHAUSTED
                continue

            self.stream_status[(log_group_name, log_stream_name)] = self.ACTIVE

            for event in response['events']:
                event['group'] = log_group_name
                event['stream'] = log_stream_name
                self.raw_events_queue.put((event['timestamp'], event))
                self.stream_max_timestamp[(log_group_name, log_stream_name)] = event['timestamp']

            if 'nextForwardToken' in response:
                self.publishers_queue.put(
                    (response['events'][-1]['timestamp'],
                     (log_group_name, log_stream_name, response['nextForwardToken']))
                )

    def _get_min_timestamp(self):
        """Return the minimum timestamp available across all active streams."""
        pending = [self.stream_max_timestamp[k] for k, v in self.stream_status.iteritems() if v != self.EXHAUSTED]
        return min(pending) if pending else None

    def _get_all_streams_exhausted(self):
        """Return if all streams are exhausted."""
        return all((s == self.EXHAUSTED for s in self.stream_status.itervalues()))

    def _raw_events_queue_consumer(self):
        """Consume events from ``raw_events_queue`` if all active streams
        have already publish events up to the ``_get_min_timestamp`` and
        register them in order into ``events_queue``."""
        while True:
            if self._get_all_streams_exhausted() and self.raw_events_queue.empty():
                if self.watch:
                    gevent.sleep(self.WATCH_SLEEP)
                    continue
                self.events_queue.put(NO_MORE_EVENTS)
                break

            try:
                timestamp, line = self.raw_events_queue.peek(timeout=1)
            except Empty:
                continue

            min_timestamp = self._get_min_timestamp()
            if min_timestamp and min_timestamp < timestamp:
                gevent.sleep(0.3)
                continue

            timestamp, line = self.raw_events_queue.get()

            output = [line['message']]
            if self.output_stream_enabled:
                output.insert(
                    0,
                    self.color(
                        line['stream'].ljust(self.max_stream_length, ' '),
                        'cyan'
                    )
                )
            if self.output_group_enabled:
                output.insert(
                    0,
                    self.color(
                        line['group'].ljust(self.max_group_length, ' '),
                        'green'
                    )
                )
            self.events_queue.put("{0}\n".format(' '.join(output)))

    def _events_consumer(self):
        """Print events from ``events_queue`` as soon as they are available."""
        while True:
            event = self.events_queue.get(True)
            if event == NO_MORE_EVENTS:
                break
            sys.stdout.write(event)
            sys.stdout.flush()

    def list_logs(self):
        self.register_publishers()

        pool = Pool(size=self.pool_size)
        pool.spawn(self._raw_events_queue_consumer)
        pool.spawn(self._events_consumer)

        if self.watch:
            pool.spawn(self.register_publishers_periodically)

        for i in xrange(self.pool_size):
            pool.spawn(self._publisher_queue_consumer)
        pool.join()

    def register_publishers(self):
        """Register publishers into ``publishers_queue``."""
        for group, stream in self._get_streams_from_patterns(self.log_group_name, self.log_stream_name):
            if (group, stream) in self.publishers:
                continue
            self.publishers.append((group, stream))
            self.max_group_length = max(self.max_group_length, len(group))
            self.max_stream_length = max(self.max_stream_length, len(stream))
            self.publishers_queue.put((0, (group, stream, None)))
            self.stream_status[(group, stream)] = self.ACTIVE
            self.stream_max_timestamp[(group, stream)] = -1

    def register_publishers_periodically(self):
        while True:
            self.register_publishers()
            gevent.sleep(2)

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
            response = self.connection.describe_log_streams(
                log_group_name=log_group_name,
                next_token=next_token
            )

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
