import sys
import unittest
from datetime import datetime
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

from botocore.compat import total_seconds
from botocore.client import ClientError
from botocore.auth import NoCredentialsError

from termcolor import colored

try:
    from mock import patch, Mock, call
except ImportError:
    from unittest.mock import patch, Mock, call

from awslogs import AWSLogs
from awslogs.exceptions import UnknownDateError
from awslogs.bin import main


class TestAWSLogs(unittest.TestCase):

    def _stream(self, name, start=0, end=sys.maxsize):
        return {'logStreamName': name,
                'firstEventTimestamp': start,
                'lastEventTimestamp': end}

    @patch('boto3.client')
    @patch('awslogs.core.datetime')
    def test_parse_datetime(self, datetime_mock, botoclient):

        awslogs = AWSLogs()
        datetime_mock.utcnow.return_value = datetime(2015, 1, 1, 3, 0, 0, 0)
        datetime_mock.return_value = datetime(1970, 1, 1)

        def epoch(dt):
            return int(total_seconds(dt - datetime(1970, 1, 1)) * 1000)

        self.assertEqual(awslogs.parse_datetime(''), None)
        self.assertEqual(awslogs.parse_datetime(None), None)

        self.assertEqual(awslogs.parse_datetime('1m'),
                         epoch(datetime(2015, 1, 1, 2, 59, 0, 0)))
        self.assertEqual(awslogs.parse_datetime('1m ago'),
                         epoch(datetime(2015, 1, 1, 2, 59, 0, 0)))
        self.assertEqual(awslogs.parse_datetime('1minute'),
                         epoch(datetime(2015, 1, 1, 2, 59, 0, 0)))
        self.assertEqual(awslogs.parse_datetime('1minute ago'),
                         epoch(datetime(2015, 1, 1, 2, 59, 0, 0)))
        self.assertEqual(awslogs.parse_datetime('1minutes'),
                         epoch(datetime(2015, 1, 1, 2, 59, 0, 0)))
        self.assertEqual(awslogs.parse_datetime('1minutes ago'),
                         epoch(datetime(2015, 1, 1, 2, 59, 0, 0)))

        self.assertEqual(awslogs.parse_datetime('1h'),
                         epoch(datetime(2015, 1, 1, 2, 0, 0, 0)))
        self.assertEqual(awslogs.parse_datetime('1h ago'),
                         epoch(datetime(2015, 1, 1, 2, 0, 0, 0)))
        self.assertEqual(awslogs.parse_datetime('1hour'),
                         epoch(datetime(2015, 1, 1, 2, 0, 0, 0)))
        self.assertEqual(awslogs.parse_datetime('1hour ago'),
                         epoch(datetime(2015, 1, 1, 2, 0, 0, 0)))
        self.assertEqual(awslogs.parse_datetime('1hours'),
                         epoch(datetime(2015, 1, 1, 2, 0, 0, 0)))
        self.assertEqual(awslogs.parse_datetime('1hours ago'),
                         epoch(datetime(2015, 1, 1, 2, 0, 0, 0)))

        self.assertEqual(awslogs.parse_datetime('1d'),
                         epoch(datetime(2014, 12, 31, 3, 0, 0, 0)))
        self.assertEqual(awslogs.parse_datetime('1d ago'),
                         epoch(datetime(2014, 12, 31, 3, 0, 0, 0)))
        self.assertEqual(awslogs.parse_datetime('1day'),
                         epoch(datetime(2014, 12, 31, 3, 0, 0, 0)))
        self.assertEqual(awslogs.parse_datetime('1day ago'),
                         epoch(datetime(2014, 12, 31, 3, 0, 0, 0)))
        self.assertEqual(awslogs.parse_datetime('1days'),
                         epoch(datetime(2014, 12, 31, 3, 0, 0, 0)))
        self.assertEqual(awslogs.parse_datetime('1days ago'),
                         epoch(datetime(2014, 12, 31, 3, 0, 0, 0)))

        self.assertEqual(awslogs.parse_datetime('1w'),
                         epoch(datetime(2014, 12, 25, 3, 0, 0, 0)))
        self.assertEqual(awslogs.parse_datetime('1w ago'),
                         epoch(datetime(2014, 12, 25, 3, 0, 0, 0)))
        self.assertEqual(awslogs.parse_datetime('1week'),
                         epoch(datetime(2014, 12, 25, 3, 0, 0, 0)))
        self.assertEqual(awslogs.parse_datetime('1week ago'),
                         epoch(datetime(2014, 12, 25, 3, 0, 0, 0)))
        self.assertEqual(awslogs.parse_datetime('1weeks'),
                         epoch(datetime(2014, 12, 25, 3, 0, 0, 0)))
        self.assertEqual(awslogs.parse_datetime('1weeks ago'),
                         epoch(datetime(2014, 12, 25, 3, 0, 0, 0)))

        self.assertEqual(awslogs.parse_datetime('1/1/2013'),
                         epoch(datetime(2013, 1, 1, 0, 0, 0, 0)))
        self.assertEqual(awslogs.parse_datetime('1/1/2012 12:34'),
                         epoch(datetime(2012, 1, 1, 12, 34, 0, 0)))
        self.assertEqual(awslogs.parse_datetime('1/1/2011 12:34:56'),
                         epoch(datetime(2011, 1, 1, 12, 34, 56, 0)))

        self.assertRaises(UnknownDateError, awslogs.parse_datetime, '???')

    @patch('boto3.client')
    def test_get_groups(self, botoclient):
        client = Mock()
        botoclient.return_value = client
        client.get_paginator.return_value.paginate.return_value = [
            {'logGroups': [{'logGroupName': 'A'},
                           {'logGroupName': 'B'},
                           {'logGroupName': 'C'}],
             'nextToken': 1},
            {'logGroups': [{'logGroupName': 'D'},
                           {'logGroupName': 'E'},
                           {'logGroupName': 'F'}],
             'nextToken': 2},
            {'logGroups': [{'logGroupName': 'G'}]},
        ]

        awslogs = AWSLogs()
        self.assertEqual([g for g in awslogs.get_groups()], ['A', 'B', 'C', 'D', 'E', 'F', 'G'])

    @patch('boto3.client')
    def test_get_streams(self, botoclient):
        client = Mock()
        botoclient.return_value = client
        client.get_paginator.return_value.paginate.return_value = [
            {'logStreams': [self._stream('A'),
                            self._stream('B'),
                            self._stream('C')],
             'nextToken': 1},
            {'logStreams': [self._stream('D'),
                            self._stream('E'),
                            self._stream('F')],
             'nextToken': 2},
            {'logStreams': [self._stream('G')]},
        ]

        awslogs = AWSLogs(log_group_name='group')
        self.assertEqual([g for g in awslogs.get_streams()], ['A', 'B', 'C', 'D', 'E', 'F', 'G'])

    @patch('boto3.client')
    @patch('awslogs.core.AWSLogs.parse_datetime')
    def test_get_streams_filtered_by_date(self, parse_datetime, botoclient):
        client = Mock()
        botoclient.return_value = client
        client.get_paginator.return_value.paginate.return_value = [
            {'logStreams': [self._stream('A', 0, 1),
                            self._stream('B', 0, 6),
                            self._stream('C'),
                            self._stream('D', sys.maxsize - 1, sys.maxsize)],
            }
        ]
        parse_datetime.side_effect = [5, 7]
        awslogs = AWSLogs(log_group_name='group', start='5', end='7')
        self.assertEqual([g for g in awslogs.get_streams()], ['B', 'C'])

    @patch('boto3.client')
    def test_get_streams_from_pattern(self, botoclient):
        client = Mock()
        botoclient.return_value = client

        side_effect = [
            {'logStreams': [self._stream('AAA'),
                            self._stream('ABA'),
                            self._stream('ACA')],
             'nextToken': 1},
            {'logStreams': [self._stream('BAA'),
                            self._stream('BBA'),
                            self._stream('BBB')],
             'nextToken': 2},
            {'logStreams': [self._stream('CAC')]},
        ]

        awslogs = AWSLogs()

        client.get_paginator.return_value.paginate.return_value = side_effect
        expected = ['AAA', 'ABA', 'ACA', 'BAA', 'BBA', 'BBB', 'CAC']
        actual = [s for s in awslogs._get_streams_from_pattern('X', 'ALL')]
        self.assertEqual(actual, expected)

        client.get_paginator.return_value.paginate.return_value = side_effect
        expected = ['AAA', 'ABA', 'ACA']
        actual = [s for s in awslogs._get_streams_from_pattern('X', 'A')]
        self.assertEqual(actual, expected)

        client.get_paginator.return_value.paginate.return_value = side_effect
        expected = ['AAA', 'ACA']
        actual = [s for s in awslogs._get_streams_from_pattern('X', 'A[AC]A')]
        self.assertEqual(actual, expected)

    @patch('boto3.client')
    @patch('sys.stdout', new_callable=StringIO)
    def test_main_get(self, mock_stdout, botoclient):
        client = Mock()
        botoclient.return_value = client
        awslogs = AWSLogs()

        logs = [
            {'events': [{'eventId': 1, 'message': 'Hello 1', 'logStreamName': 'DDD'},
                        {'eventId': 2, 'message': 'Hello 2', 'logStreamName': 'EEE'},
                        {'eventId': 3, 'message': 'Hello 3', 'logStreamName': 'DDD'}],
             'nextToken': 'token'},
            {'events': [{'eventId': 4, 'message': 'Hello 4', 'logStreamName': 'EEE'},
                        {'eventId': 5, 'message': 'Hello 5', 'logStreamName': 'DDD'},
                        {'eventId': 6, 'message': 'Hello 6', 'logStreamName': 'EEE'}],
             'nextToken': 'token'},
            {'events': []}
        ]

        groups = [
            {'logGroups': [{'logGroupName': 'AAA'},
                           {'logGroupName': 'BBB'},
                           {'logGroupName': 'CCC'}]},
        ]

        streams = [
            {'logStreams': [self._stream('DDD'),
                            self._stream('EEE')]}
        ]

        def paginator(value):
            mock = Mock()
            mock.paginate.return_value = {
                'describe_log_groups': groups,
                'describe_log_streams': streams
            }.get(value)
            return mock

        client.get_paginator.side_effect = paginator
        client.filter_log_events.side_effect = logs
        main("awslogs get AAA DDD --no-color".split())

        self.assertEqual(
            mock_stdout.getvalue(),
            ("AAA DDD Hello 1\n"
             "AAA EEE Hello 2\n"
             "AAA DDD Hello 3\n"
             "AAA EEE Hello 4\n"
             "AAA DDD Hello 5\n"
             "AAA EEE Hello 6\n")
        )

    @patch('boto3.client')
    @patch('sys.stdout', new_callable=StringIO)
    def test_main_get_deduplication(self, mock_stdout, botoclient):
        client = Mock()
        botoclient.return_value = client
        awslogs = AWSLogs()

        logs = [
            {'events': [{'eventId': 1, 'message': 'Hello 1', 'logStreamName': 'DDD'},
                        {'eventId': 2, 'message': 'Hello 2', 'logStreamName': 'EEE'},
                        {'eventId': 3, 'message': 'Hello 3', 'logStreamName': 'DDD'}],
             'nextToken': 'token'},
            {'events': [{'eventId': 1, 'message': 'Hello 1', 'logStreamName': 'DDD'},
                        {'eventId': 2, 'message': 'Hello 2', 'logStreamName': 'EEE'},
                        {'eventId': 3, 'message': 'Hello 3', 'logStreamName': 'DDD'}],
             'nextToken': 'token'},
            {'events': []}
        ]

        groups = [
            {'logGroups': [{'logGroupName': 'AAA'},
                           {'logGroupName': 'BBB'},
                           {'logGroupName': 'CCC'}]},
        ]

        streams = [
            {'logStreams': [self._stream('DDD'),
                            self._stream('EEE')]}
        ]

        def paginator(value):
            mock = Mock()
            mock.paginate.return_value = {
                'describe_log_groups': groups,
                'describe_log_streams': streams
            }.get(value)
            return mock

        client.get_paginator.side_effect = paginator
        client.filter_log_events.side_effect = logs
        main("awslogs get AAA DDD --no-color".split())

        self.assertEqual(
            mock_stdout.getvalue(),
            ("AAA DDD Hello 1\n"
             "AAA EEE Hello 2\n"
             "AAA DDD Hello 3\n")
        )

    @patch('boto3.client')
    @patch('sys.stdout', new_callable=StringIO)
    def test_main_groups(self, mock_stdout, botoclient):
        client = Mock()
        botoclient.return_value = client
        awslogs = AWSLogs()

        groups = [
            {'logGroups': [{'logGroupName': 'AAA'},
                           {'logGroupName': 'BBB'},
                           {'logGroupName': 'CCC'}]},
        ]

        client.get_paginator.return_value.paginate.return_value = groups

        main("awslogs groups".split())
        self.assertEqual(
            mock_stdout.getvalue(),
            ("AAA\n"
             "BBB\n"
             "CCC\n")
        )

    @patch('boto3.client')
    @patch('sys.stdout', new_callable=StringIO)
    def test_main_streams(self, mock_stdout, botoclient):
        client = Mock()
        botoclient.return_value = client
        awslogs = AWSLogs()

        groups = [
            {'logGroups': [{'logGroupName': 'AAA'},
                           {'logGroupName': 'BBB'},
                           {'logGroupName': 'CCC'}]},
        ]

        streams = [
            {'logStreams': [self._stream('DDD'),
                            self._stream('EEE')]}
        ]

        def paginator(value):
            mock = Mock()
            mock.paginate.return_value = {
                'describe_log_groups': groups,
                'describe_log_streams': streams
            }.get(value)
            return mock

        client.get_paginator.side_effect = paginator

        main("awslogs streams AAA".split())
        self.assertEqual(
            mock_stdout.getvalue(),
            ("DDD\n"
             "EEE\n")
        )

    @patch('sys.stderr', new_callable=StringIO)
    def test_unknown_date_error(self, mock_stderr):
        code = main("awslogs get AAA BBB -sX".split())
        self.assertEqual(code, 3)
        self.assertEqual(mock_stderr.getvalue(),
                         colored("awslogs doesn't understand 'X' as a date.\n", "red"))

    @patch('awslogs.bin.AWSLogs')
    @patch('sys.stderr', new_callable=StringIO)
    def test_unknown_error(self, mock_stderr, mock_awslogs):
        mock_awslogs.side_effect = Exception("Error!")
        code = main("awslogs get AAA BBB".split())
        output = mock_stderr.getvalue()
        self.assertEqual(code, 1)
        self.assertTrue("You've found a bug!" in output)
        self.assertTrue("Exception: Error!" in output)
