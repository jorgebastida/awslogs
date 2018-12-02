import sys
import unittest
from datetime import datetime
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

from botocore.compat import total_seconds
from termcolor import colored

try:
    from mock import patch, Mock
except ImportError:
    from unittest.mock import patch, Mock

from awslogs import AWSLogs
from awslogs.exceptions import UnknownDateError
from awslogs.bin import main


def mapkeys(keys, rec_lst):
    """Convert list of list into list of dicts with given keys
    >>> keys = ["a", "b", "c"]
    >>> rec_lst = [[1, 2, 3], [4, 5, 6]]
    >>> mapkeys(keys, rec_lst)
    [{"a": 1, "b": 2, "c": 3}, {"a": 4, "b": 5, "c": 6}]
    """
    return [dict(zip(keys, vals)) for vals in rec_lst]


class TestAWSLogsDatetimeParse(unittest.TestCase):
    @patch('awslogs.core.boto3_client')
    @patch('awslogs.core.datetime')
    def test_parse_datetime(self, datetime_mock, botoclient):

        awslogs = AWSLogs()
        datetime_mock.utcnow.return_value = datetime(2015, 1, 1, 3, 0, 0, 0)
        datetime_mock.return_value = datetime(1970, 1, 1)

        def iso2epoch(iso_str):
            dt = datetime.strptime(iso_str, "%Y-%m-%d %H:%M:%S")
            return int(total_seconds(dt - datetime(1970, 1, 1)) * 1000)

        self.assertEqual(awslogs.parse_datetime(''), None)
        self.assertEqual(awslogs.parse_datetime(None), None)
        plan = (('2015-01-01 02:59:00', '1m'),
                ('2015-01-01 02:59:00', '1m ago'),
                ('2015-01-01 02:59:00', '1minute'),
                ('2015-01-01 02:59:00', '1minute ago'),
                ('2015-01-01 02:59:00', '1minutes'),
                ('2015-01-01 02:59:00', '1minutes ago'),

                ('2015-01-01 02:00:00', '1h'),
                ('2015-01-01 02:00:00', '1h ago'),
                ('2015-01-01 02:00:00', '1hour'),
                ('2015-01-01 02:00:00', '1hour ago'),
                ('2015-01-01 02:00:00', '1hours'),
                ('2015-01-01 02:00:00', '1hours ago'),

                ('2014-12-31 03:00:00', '1d'),
                ('2014-12-31 03:00:00', '1d ago'),
                ('2014-12-31 03:00:00', '1day'),
                ('2014-12-31 03:00:00', '1day ago'),
                ('2014-12-31 03:00:00', '1days'),
                ('2014-12-31 03:00:00', '1days ago'),

                ('2014-12-25 03:00:00', '1w'),
                ('2014-12-25 03:00:00', '1w ago'),
                ('2014-12-25 03:00:00', '1week'),
                ('2014-12-25 03:00:00', '1week ago'),
                ('2014-12-25 03:00:00', '1weeks'),
                ('2014-12-25 03:00:00', '1weeks ago'),

                ('2013-01-01 00:00:00', '1/1/2013'),
                ('2012-01-01 12:34:00', '1/1/2012 12:34'),
                ('2011-01-01 12:34:56', '1/1/2011 12:34:56'),

                ('2016-08-31 02:23:25', '2016-08-31T02:23:25.000Z'),
                ('2016-08-31 02:23:25', '2016-08-31 10:23:25 UTC-8')
                )

        for expected_iso, dateutil_time in plan:
            self.assertEqual(awslogs.parse_datetime(dateutil_time),
                             iso2epoch(expected_iso))

        self.assertRaises(UnknownDateError, awslogs.parse_datetime, '???')


class TestAWSLogs(unittest.TestCase):

    def _stream(self, name, start=0, ingestion=sys.maxsize, end=None):
        if end is None:
            end = ingestion - 1
        return {'logStreamName': name,
                'firstEventTimestamp': start,
                'lastEventTimestamp': end,
                'lastIngestionTime': ingestion}

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

    def set_json_logs(self, botoclient):
        client = Mock()
        botoclient.return_value = client

        event_keys = ["eventId", "timestamp", "ingestionTime",
                      "message", "logStreamName"]
        logs = [
            {'events': mapkeys(event_keys,
                               [[1, 0, 5000, '{"foo": "bar"}', "DDD"],
                                [2, 0, 5000, '{"foo": {"bar": "baz"}}', "EEE"],
                                [3, 0, 5006, "Hello 3", "DDD"]]),
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

    @patch('awslogs.core.boto3_client')
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

    @patch('awslogs.core.boto3_client')
    def test_get_groups_with_log_group_prefix(self, botoclient):
        client = Mock()
        botoclient.return_value = client
        client.get_paginator.return_value.paginate.return_value = [
            {'logGroups': [{'logGroupName': 'A'}]}
        ]

        awslogs = AWSLogs(log_group_prefix='log_group_prefix')
        self.assertEqual([g for g in awslogs.get_groups()],
                         ['A'])

    @patch('awslogs.core.boto3_client')
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

    @patch('awslogs.core.boto3_client')
    @patch('awslogs.core.AWSLogs.parse_datetime')
    def test_get_streams_filtered_by_date(self, parse_datetime, botoclient):
        client = Mock()
        botoclient.return_value = client
        client.get_paginator.return_value.paginate.return_value = [
            {'logStreams': [self._stream('A', 0, 1),
                            self._stream('B', 0, 6),
                            self._stream('C'),
                            self._stream('D', sys.maxsize - 1, sys.maxsize),
                            self._stream('E', 0, 5, 4),
                            ],
             }
        ]
        parse_datetime.side_effect = [5, 7]
        awslogs = AWSLogs(log_group_name='group', start='5', end='7')
        self.assertEqual([g for g in awslogs.get_streams()], ['B', 'C', 'E'])

    @patch('awslogs.core.boto3_client')
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

    @patch('awslogs.core.boto3_client')
    @patch('sys.stdout', new_callable=StringIO)
    def test_main_get(self, mock_stdout, botoclient):
        self.set_ABCDE_logs(botoclient)
        exit_code = main("awslogs get AAA DDD --color=never".split())
        output = mock_stdout.getvalue()
        expected = ("AAA DDD Hello 1\n"
                    "AAA EEE Hello 2\n"
                    "AAA DDD Hello 3\n"
                    "AAA EEE Hello 4\n"
                    "AAA DDD Hello 5\n"
                    "AAA EEE Hello 6\n"
                    )
        assert output == expected
        assert exit_code == 0

    @patch('awslogs.core.boto3_client')
    @patch('sys.stdout', new_callable=StringIO)
    def test_main_get_with_color(self, mock_stdout, botoclient):
        self.set_ABCDE_logs(botoclient)
        exit_code = main("awslogs get AAA DDD".split())
        output = mock_stdout.getvalue()
        expected = ("\x1b[32mAAA\x1b[0m \x1b[36mDDD\x1b[0m Hello 1\n"
                    "\x1b[32mAAA\x1b[0m \x1b[36mEEE\x1b[0m Hello 2\n"
                    "\x1b[32mAAA\x1b[0m \x1b[36mDDD\x1b[0m Hello 3\n"
                    "\x1b[32mAAA\x1b[0m \x1b[36mEEE\x1b[0m Hello 4\n"
                    "\x1b[32mAAA\x1b[0m \x1b[36mDDD\x1b[0m Hello 5\n"
                    "\x1b[32mAAA\x1b[0m \x1b[36mEEE\x1b[0m Hello 6\n"
                    )
        assert output == expected
        assert exit_code == 0

    @patch('awslogs.core.boto3_client')
    @patch('sys.stdout', new_callable=StringIO)
    def test_main_get_query(self, mock_stdout, botoclient):
        self.set_json_logs(botoclient)
        exit_code = main("awslogs get AAA DDD --query foo".split())
        output = mock_stdout.getvalue()
        expected = ("\x1b[32mAAA\x1b[0m \x1b[36mDDD\x1b[0m bar\n"
                    "\x1b[32mAAA\x1b[0m \x1b[36mEEE\x1b[0m {\"bar\": \"baz\"}\n"
                    "\x1b[32mAAA\x1b[0m \x1b[36mDDD\x1b[0m Hello 3\n"
                    )
        assert output == expected
        assert exit_code == 0

    @patch('awslogs.core.boto3_client')
    @patch('sys.stdout', new_callable=StringIO)
    def test_get_nogroup(self, mock_stdout, botoclient):
        self.set_ABCDE_logs(botoclient)
        exit_code = main("awslogs get --no-group AAA DDD --color=never".split())

        self.assertEqual(
            mock_stdout.getvalue(),
            ("DDD Hello 1\n"
             "EEE Hello 2\n"
             "DDD Hello 3\n"
             "EEE Hello 4\n"
             "DDD Hello 5\n"
             "EEE Hello 6\n")
        )
        assert exit_code == 0

    @patch('awslogs.core.boto3_client')
    @patch('sys.stdout', new_callable=StringIO)
    def test_get_nostream(self, mock_stdout, botoclient):
        self.set_ABCDE_logs(botoclient)
        exit_code = main("awslogs get --no-stream AAA DDD --color=never".split())

        self.assertEqual(
            mock_stdout.getvalue(),
            ("AAA Hello 1\n"
             "AAA Hello 2\n"
             "AAA Hello 3\n"
             "AAA Hello 4\n"
             "AAA Hello 5\n"
             "AAA Hello 6\n")
        )
        assert exit_code == 0

    @patch('awslogs.core.boto3_client')
    @patch('sys.stdout', new_callable=StringIO)
    def test_get_nogroup_nostream(self, mock_stdout, botoclient):
        self.set_ABCDE_logs(botoclient)
        exit_code = main("awslogs get --no-group --no-stream AAA DDD --color=never".split())

        self.assertEqual(
            mock_stdout.getvalue(),
            ("Hello 1\n"
             "Hello 2\n"
             "Hello 3\n"
             "Hello 4\n"
             "Hello 5\n"
             "Hello 6\n")
        )
        assert exit_code == 0

    @patch('awslogs.core.boto3_client')
    @patch('sys.stdout', new_callable=StringIO)
    def test_get_nogroup_nostream_short_forms(self, mock_stdout, botoclient):
        self.set_ABCDE_logs(botoclient)
        exit_code = main("awslogs get -GS AAA DDD --color=never".split())

        self.assertEqual(
            mock_stdout.getvalue(),
            ("Hello 1\n"
             "Hello 2\n"
             "Hello 3\n"
             "Hello 4\n"
             "Hello 5\n"
             "Hello 6\n")
        )
        assert exit_code == 0

    @patch('awslogs.core.boto3_client')
    @patch('sys.stdout', new_callable=StringIO)
    def test_get_timestamp(self, mock_stdout, botoclient):
        self.set_ABCDE_logs(botoclient)
        exit_code = main("awslogs get "
             "--timestamp --no-group --no-stream "
             "AAA DDD --color=never".split())

        self.assertEqual(
            mock_stdout.getvalue(),
            ("1970-01-01T00:00:00.000Z Hello 1\n"
             "1970-01-01T00:00:00.000Z Hello 2\n"
             "1970-01-01T00:00:00.000Z Hello 3\n"
             "1970-01-01T00:00:00.000Z Hello 4\n"
             "1970-01-01T00:00:00.000Z Hello 5\n"
             "1970-01-01T00:00:00.000Z Hello 6\n")
        )
        assert exit_code == 0

    @patch('awslogs.core.boto3_client')
    @patch('sys.stdout', new_callable=StringIO)
    def test_get_ingestion_time(self, mock_stdout, botoclient):
        self.set_ABCDE_logs(botoclient)
        exit_code = main("awslogs get "
             "--ingestion-time --no-group --no-stream "
             "AAA DDD --color=never".split())

        self.assertEqual(
            mock_stdout.getvalue(),
            ("1970-01-01T00:00:05.000Z Hello 1\n"
             "1970-01-01T00:00:05.000Z Hello 2\n"
             "1970-01-01T00:00:05.006Z Hello 3\n"
             "1970-01-01T00:00:05.000Z Hello 4\n"
             "1970-01-01T00:00:05.000Z Hello 5\n"
             "1970-01-01T00:00:05.009Z Hello 6\n")
        )
        assert exit_code == 0

    @patch('awslogs.core.boto3_client')
    @patch('sys.stdout', new_callable=StringIO)
    def test_get_timestamp_and_ingestion_time(self, mock_stdout, botoclient):
        self.set_ABCDE_logs(botoclient)
        exit_code = main("awslogs get "
             "--timestamp --ingestion-time --no-group --no-stream "
             "AAA DDD --color=never".split())

        self.assertEqual(
            mock_stdout.getvalue(),
            ("1970-01-01T00:00:00.000Z 1970-01-01T00:00:05.000Z Hello 1\n"
             "1970-01-01T00:00:00.000Z 1970-01-01T00:00:05.000Z Hello 2\n"
             "1970-01-01T00:00:00.000Z 1970-01-01T00:00:05.006Z Hello 3\n"
             "1970-01-01T00:00:00.000Z 1970-01-01T00:00:05.000Z Hello 4\n"
             "1970-01-01T00:00:00.000Z 1970-01-01T00:00:05.000Z Hello 5\n"
             "1970-01-01T00:00:00.000Z 1970-01-01T00:00:05.009Z Hello 6\n")
        )
        assert exit_code == 0

    @patch('awslogs.core.boto3_client')
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
        exit_code = main("awslogs get AAA DDD --color=never".split())

        self.assertEqual(
            mock_stdout.getvalue(),
            ("AAA DDD Hello 1\n"
             "AAA EEE Hello 2\n"
             "AAA DDD Hello 3\n")
        )
        assert exit_code == 0

    @patch('awslogs.core.boto3_client')
    @patch('sys.stderr', new_callable=StringIO)
    def test_main_get_no_matching_streams(self, mock_stderr, botoclient):
        client = Mock()
        botoclient.return_value = client

        groups = [
            {'logGroups': [{'logGroupName': 'AAA'}]},
        ]

        # None of these match the pattern below: "foo.*"
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

        exit_code = main("awslogs get AAA foo.*".split())
        self.assertEqual(mock_stderr.getvalue(),
                         colored("No streams match your pattern 'foo.*' "
                                 "for the given time period.\n",
                                 "red"))
        assert exit_code == 7

    @patch('awslogs.core.boto3_client')
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

        exit_code = main("awslogs groups".split())
        self.assertEqual(
            mock_stdout.getvalue(),
            ("AAA\n"
             "BBB\n"
             "CCC\n")
        )
        assert exit_code == 0

    @patch('awslogs.core.boto3_client')
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

        exit_code = main("awslogs streams AAA".split())
        self.assertEqual(
            mock_stdout.getvalue(),
            ("DDD\n"
             "EEE\n")
        )
        assert exit_code == 0

    @patch('sys.stderr', new_callable=StringIO)
    def test_unknown_date_error(self, mock_stderr):
        exit_code = main("awslogs get AAA BBB -sX".split())
        self.assertEqual(mock_stderr.getvalue(),
                         colored("awslogs doesn't understand 'X' as a date.\n",
                                 "red"))
        assert exit_code == 3

    @patch('awslogs.bin.AWSLogs')
    @patch('sys.stderr', new_callable=StringIO)
    def test_unknown_error(self, mock_stderr, mock_awslogs):
        mock_awslogs.side_effect = Exception("Error!")
        exit_code = main("awslogs get AAA BBB".split())
        output = mock_stderr.getvalue()
        self.assertTrue("You've found a bug!" in output)
        self.assertTrue("Exception: Error!" in output)
        assert exit_code == 1

    @patch('sys.stderr', new_callable=StringIO)
    def test_help(self, mock_stderr):
        self.assertRaises(SystemExit, main, "awslogs --help".split())

    @patch('sys.stderr', new_callable=StringIO)
    def test_version(self, mock_stderr):
        self.assertRaises(SystemExit, main, "awslogs --version".split())

    @patch('botocore.session.get_session')
    def test_boto3_client_creation(self, mock_core_session):
        client = Mock()
        boto_session = Mock()
        mock_core_session.return_value = boto_session
        boto_session.create_client.return_value = client

        awslogs = AWSLogs()
        self.assertEqual(client, awslogs.client)
