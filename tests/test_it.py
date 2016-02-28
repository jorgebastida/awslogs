import sys
import unittest

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

from termcolor import colored

try:
    from mock import patch, Mock
except ImportError:
    from unittest.mock import patch, Mock

from awslogs import AWSLogs
from awslogs.bin import main


def mapkeys(keys, rec_lst):
    """Convert list of list into list of dicts with given keys
    >>> keys = ["a", "b", "c"]
    >>> rec_lst = [[1, 2, 3], [4, 5, 6]]
    >>> mapkeys(keys, rec_lst)
    [{"a": 1, "b": 2, "c": 3}, {"a": 4, "b": 5, "c": 6}]
    """
    return [dict(zip(keys, vals)) for vals in rec_lst]


class TestAWSLogs(unittest.TestCase):

    def _stream(self, name, start=0, end=sys.maxsize):
        return {'logStreamName': name,
                'firstEventTimestamp': start,
                'lastEventTimestamp': end}

    def set_ABCDE_logs(self, botoclient):
        client = Mock()
        botoclient.return_value = client
        # awslogs = AWSLogs()

        event_keys = ["eventId", "timestamp", "ingestionTime",
                      "message", "logStreamName"]
        logs = [
            {'events': mapkeys(event_keys,
                               [[1, 0, 5000, "Hello 1", "DDD"],
                                [2, 0, 5000, "Hello 2", "EEE"],
                                [3, 0, 5006, "Hello 3", "DDD"]]),
             'nextToken': 'token'},
            {'events': mapkeys(event_keys,
                               [[4, 0, 5000, "Hello 4", "EEE"],
                                [5, 0, 5000, "Hello 5", "DDD"],
                                [6, 0, 5009, "Hello 6", "EEE"]]),
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
        self.assertEqual([g for g in awslogs.get_groups()],
                         ['A', 'B', 'C', 'D', 'E', 'F', 'G'])

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
        self.assertEqual([g for g in awslogs.get_streams()],
                         ['A', 'B', 'C', 'D', 'E', 'F', 'G'])

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
        self.set_ABCDE_logs(botoclient)
        main("awslogs get AAA DDD --no-color".split())
        output = mock_stdout.getvalue()
        expected = ("AAA DDD Hello 1\n"
                    "AAA EEE Hello 2\n"
                    "AAA DDD Hello 3\n"
                    "AAA EEE Hello 4\n"
                    "AAA DDD Hello 5\n"
                    "AAA EEE Hello 6\n"
                    )
        assert output == expected

    @patch('boto3.client')
    @patch('sys.stdout', new_callable=StringIO)
    def test_main_get_with_color(self, mock_stdout, botoclient):
        self.set_ABCDE_logs(botoclient)
        main("awslogs get AAA DDD".split())
        output = mock_stdout.getvalue()
        expected = ("\x1b[32mAAA\x1b[0m \x1b[36mDDD\x1b[0m Hello 1\n"
                    "\x1b[32mAAA\x1b[0m \x1b[36mEEE\x1b[0m Hello 2\n"
                    "\x1b[32mAAA\x1b[0m \x1b[36mDDD\x1b[0m Hello 3\n"
                    "\x1b[32mAAA\x1b[0m \x1b[36mEEE\x1b[0m Hello 4\n"
                    "\x1b[32mAAA\x1b[0m \x1b[36mDDD\x1b[0m Hello 5\n"
                    "\x1b[32mAAA\x1b[0m \x1b[36mEEE\x1b[0m Hello 6\n"
                    )

        assert output == expected

    @patch('boto3.client')
    @patch('sys.stdout', new_callable=StringIO)
    def test_get_nogroup(self, mock_stdout, botoclient):
        self.set_ABCDE_logs(botoclient)
        main("awslogs get --no-group AAA DDD --no-color".split())

        self.assertEqual(
            mock_stdout.getvalue(),
            ("DDD Hello 1\n"
             "EEE Hello 2\n"
             "DDD Hello 3\n"
             "EEE Hello 4\n"
             "DDD Hello 5\n"
             "EEE Hello 6\n")
        )

    @patch('boto3.client')
    @patch('sys.stdout', new_callable=StringIO)
    def test_get_nostream(self, mock_stdout, botoclient):
        self.set_ABCDE_logs(botoclient)
        main("awslogs get --no-stream AAA DDD --no-color".split())

        self.assertEqual(
            mock_stdout.getvalue(),
            ("AAA Hello 1\n"
             "AAA Hello 2\n"
             "AAA Hello 3\n"
             "AAA Hello 4\n"
             "AAA Hello 5\n"
             "AAA Hello 6\n")
        )

    @patch('boto3.client')
    @patch('sys.stdout', new_callable=StringIO)
    def test_get_nogroup_nostream(self, mock_stdout, botoclient):
        self.set_ABCDE_logs(botoclient)
        main("awslogs get --no-group --no-stream AAA DDD --no-color".split())

        self.assertEqual(
            mock_stdout.getvalue(),
            ("Hello 1\n"
             "Hello 2\n"
             "Hello 3\n"
             "Hello 4\n"
             "Hello 5\n"
             "Hello 6\n")
        )

    @patch('boto3.client')
    @patch('sys.stdout', new_callable=StringIO)
    def test_get_timestamp(self, mock_stdout, botoclient):
        self.set_ABCDE_logs(botoclient)
        main("awslogs get "
             "--timestamp --no-group --no-stream "
             "AAA DDD --no-color".split())

        self.assertEqual(
            mock_stdout.getvalue(),
            ("1970-01-01T00:00:00.000Z Hello 1\n"
             "1970-01-01T00:00:00.000Z Hello 2\n"
             "1970-01-01T00:00:00.000Z Hello 3\n"
             "1970-01-01T00:00:00.000Z Hello 4\n"
             "1970-01-01T00:00:00.000Z Hello 5\n"
             "1970-01-01T00:00:00.000Z Hello 6\n")
        )

    @patch('boto3.client')
    @patch('sys.stdout', new_callable=StringIO)
    def test_get_ingestion_time(self, mock_stdout, botoclient):
        self.set_ABCDE_logs(botoclient)
        main("awslogs get "
             "--ingestion-time --no-group --no-stream "
             "AAA DDD --no-color".split())

        self.assertEqual(
            mock_stdout.getvalue(),
            ("1970-01-01T00:00:05.000Z Hello 1\n"
             "1970-01-01T00:00:05.000Z Hello 2\n"
             "1970-01-01T00:00:05.006Z Hello 3\n"
             "1970-01-01T00:00:05.000Z Hello 4\n"
             "1970-01-01T00:00:05.000Z Hello 5\n"
             "1970-01-01T00:00:05.009Z Hello 6\n")
        )

    @patch('boto3.client')
    @patch('sys.stdout', new_callable=StringIO)
    def test_get_timestamp_and_ingestion_time(self, mock_stdout, botoclient):
        self.set_ABCDE_logs(botoclient)
        main("awslogs get "
             "--timestamp --ingestion-time --no-group --no-stream "
             "AAA DDD --no-color".split())

        self.assertEqual(
            mock_stdout.getvalue(),
            ("1970-01-01T00:00:00.000Z 1970-01-01T00:00:05.000Z Hello 1\n"
             "1970-01-01T00:00:00.000Z 1970-01-01T00:00:05.000Z Hello 2\n"
             "1970-01-01T00:00:00.000Z 1970-01-01T00:00:05.006Z Hello 3\n"
             "1970-01-01T00:00:00.000Z 1970-01-01T00:00:05.000Z Hello 4\n"
             "1970-01-01T00:00:00.000Z 1970-01-01T00:00:05.000Z Hello 5\n"
             "1970-01-01T00:00:00.000Z 1970-01-01T00:00:05.009Z Hello 6\n")
        )

    @patch('boto3.client')
    @patch('sys.stdout', new_callable=StringIO)
    def test_main_get_deduplication(self, mock_stdout, botoclient):
        client = Mock()
        botoclient.return_value = client

        event_keys = ["eventId", "timestamp", "ingestionTime",
                      "message", "logStreamName"]
        logs = [
            {'events': mapkeys(event_keys,
                               [[1, 0, 0, 'Hello 1', 'DDD'],
                                [2, 0, 0, 'Hello 2', 'EEE'],
                                [3, 0, 0, 'Hello 3', 'DDD']]),
             'nextToken': 'token'},
            {'events': mapkeys(event_keys,
                               [[1, 0, 0, 'Hello 1', 'EEE'],
                                [2, 0, 0, 'Hello 2', 'DDD'],
                                [3, 0, 0, 'Hello 3', 'EEE']]),
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
                         colored("awslogs doesn't understand 'X' as a date.\n",
                                 "red"))

    @patch('awslogs.bin.AWSLogs')
    @patch('sys.stderr', new_callable=StringIO)
    def test_unknown_error(self, mock_stderr, mock_awslogs):
        mock_awslogs.side_effect = Exception("Error!")
        code = main("awslogs get AAA BBB".split())
        output = mock_stderr.getvalue()
        self.assertEqual(code, 1)
        self.assertTrue("You've found a bug!" in output)
        self.assertTrue("Exception: Error!" in output)

    @patch('sys.stderr', new_callable=StringIO)
    def test_help(self, mock_stderr):
        self.assertRaises(SystemExit, main, "awslogs --help".split())

    @patch('sys.stderr', new_callable=StringIO)
    def test_version(self, mock_stderr):
        self.assertRaises(SystemExit, main, "awslogs --version".split())
