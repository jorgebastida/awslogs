import unittest
from datetime import datetime
from StringIO import StringIO

import gevent
from gevent.pool import Pool

from mock import Mock, patch, call

from awslogs import AWSLogs
from awslogs.exceptions import UnknownDateError
from awslogs.core import NO_MORE_EVENTS
from awslogs.bin import main


class TestAWSLogs(unittest.TestCase):

    def setUp(self):
        super(TestAWSLogs, self).setUp()
        self.aws = AWSLogs(connection_cls=Mock)

    @patch('awslogs.core.datetime')
    def test_parse_datetime(self, datetime_mock):
        datetime_mock.now.return_value = datetime(2015, 1, 1, 3, 0, 0, 0)

        def epoch(dt):
            return int(dt.strftime("%s")) * 1000

        self.assertEqual(self.aws.parse_datetime(''), None)
        self.assertEqual(self.aws.parse_datetime(None), None)

        self.assertEqual(self.aws.parse_datetime('1m'),
                         epoch(datetime(2015, 1, 1, 2, 59, 0, 0)))
        self.assertEqual(self.aws.parse_datetime('1m ago'),
                         epoch(datetime(2015, 1, 1, 2, 59, 0, 0)))
        self.assertEqual(self.aws.parse_datetime('1minute'),
                         epoch(datetime(2015, 1, 1, 2, 59, 0, 0)))
        self.assertEqual(self.aws.parse_datetime('1minute ago'),
                         epoch(datetime(2015, 1, 1, 2, 59, 0, 0)))
        self.assertEqual(self.aws.parse_datetime('1minutes'),
                         epoch(datetime(2015, 1, 1, 2, 59, 0, 0)))
        self.assertEqual(self.aws.parse_datetime('1minutes ago'),
                         epoch(datetime(2015, 1, 1, 2, 59, 0, 0)))

        self.assertEqual(self.aws.parse_datetime('1h'),
                         epoch(datetime(2015, 1, 1, 2, 0, 0, 0)))
        self.assertEqual(self.aws.parse_datetime('1h ago'),
                         epoch(datetime(2015, 1, 1, 2, 0, 0, 0)))
        self.assertEqual(self.aws.parse_datetime('1hour'),
                         epoch(datetime(2015, 1, 1, 2, 0, 0, 0)))
        self.assertEqual(self.aws.parse_datetime('1hour ago'),
                         epoch(datetime(2015, 1, 1, 2, 0, 0, 0)))
        self.assertEqual(self.aws.parse_datetime('1hours'),
                         epoch(datetime(2015, 1, 1, 2, 0, 0, 0)))
        self.assertEqual(self.aws.parse_datetime('1hours ago'),
                         epoch(datetime(2015, 1, 1, 2, 0, 0, 0)))

        self.assertEqual(self.aws.parse_datetime('1d'),
                         epoch(datetime(2014, 12, 31, 3, 0, 0, 0)))
        self.assertEqual(self.aws.parse_datetime('1d ago'),
                         epoch(datetime(2014, 12, 31, 3, 0, 0, 0)))
        self.assertEqual(self.aws.parse_datetime('1day'),
                         epoch(datetime(2014, 12, 31, 3, 0, 0, 0)))
        self.assertEqual(self.aws.parse_datetime('1day ago'),
                         epoch(datetime(2014, 12, 31, 3, 0, 0, 0)))
        self.assertEqual(self.aws.parse_datetime('1days'),
                         epoch(datetime(2014, 12, 31, 3, 0, 0, 0)))
        self.assertEqual(self.aws.parse_datetime('1days ago'),
                         epoch(datetime(2014, 12, 31, 3, 0, 0, 0)))

        self.assertEqual(self.aws.parse_datetime('1w'),
                         epoch(datetime(2014, 12, 25, 3, 0, 0, 0)))
        self.assertEqual(self.aws.parse_datetime('1w ago'),
                         epoch(datetime(2014, 12, 25, 3, 0, 0, 0)))
        self.assertEqual(self.aws.parse_datetime('1week'),
                         epoch(datetime(2014, 12, 25, 3, 0, 0, 0)))
        self.assertEqual(self.aws.parse_datetime('1week ago'),
                         epoch(datetime(2014, 12, 25, 3, 0, 0, 0)))
        self.assertEqual(self.aws.parse_datetime('1weeks'),
                         epoch(datetime(2014, 12, 25, 3, 0, 0, 0)))
        self.assertEqual(self.aws.parse_datetime('1weeks ago'),
                         epoch(datetime(2014, 12, 25, 3, 0, 0, 0)))

        self.assertEqual(self.aws.parse_datetime('1/1/2013'),
                         epoch(datetime(2013, 1, 1, 0, 0, 0, 0)))
        self.assertEqual(self.aws.parse_datetime('1/1/2012 12:34'),
                         epoch(datetime(2012, 1, 1, 12, 34, 0, 0)))
        self.assertEqual(self.aws.parse_datetime('1/1/2011 12:34:56'),
                         epoch(datetime(2011, 1, 1, 12, 34, 56, 0)))

        self.assertRaises(UnknownDateError, self.aws.parse_datetime, '???')

    def test_get_groups(self):
        self.aws.connection.describe_log_groups.side_effect = [
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

        expected = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
        self.assertEqual([g for g in self.aws.get_groups()], expected)

        expected = [call(next_token=None),
                    call(next_token=1),
                    call(next_token=2)]

        self.assertEqual(self.aws.connection.describe_log_groups.call_args_list,
                         expected)

    def test_get_streams(self):
        self.aws.connection.describe_log_streams.side_effect = [
            {'logStreams': [{'logStreamName': 'A'},
                            {'logStreamName': 'B'},
                            {'logStreamName': 'C'}],
             'nextToken': 1},
            {'logStreams': [{'logStreamName': 'D'},
                            {'logStreamName': 'E'},
                            {'logStreamName': 'F'}],
             'nextToken': 2},
            {'logStreams': [{'logStreamName': 'G'}]},
        ]

        expected = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
        self.assertEqual([g for g in self.aws.get_streams('group')], expected)

        expected = [call(log_group_name="group", next_token=None),
                    call(log_group_name="group", next_token=1),
                    call(log_group_name="group", next_token=2)]

        self.assertEqual(self.aws.connection.describe_log_streams.call_args_list,
                         expected)

    def test_get_streams_from_pattern(self):
        side_effect = [
            {'logStreams': [{'logStreamName': 'AAA'},
                            {'logStreamName': 'ABA'},
                            {'logStreamName': 'ACA'}],
             'nextToken': 1},
            {'logStreams': [{'logStreamName': 'BAA'},
                            {'logStreamName': 'BBA'},
                            {'logStreamName': 'BBB'}],
             'nextToken': 2},
            {'logStreams': [{'logStreamName': 'CAC'}]},
        ]

        self.aws.connection.describe_log_streams.side_effect = side_effect
        expected = ['AAA', 'ABA', 'ACA', 'BAA', 'BBA', 'BBB', 'CAC']
        actual = [s for s in self.aws._get_streams_from_pattern('X', 'ALL')]
        self.assertEqual(actual, expected)

        self.aws.connection.describe_log_streams.side_effect = side_effect
        expected = ['AAA', 'ABA', 'ACA']
        actual = [s for s in self.aws._get_streams_from_pattern('X', 'A')]
        self.assertEqual(actual, expected)

        self.aws.connection.describe_log_streams.side_effect = side_effect
        expected = ['AAA', 'ACA']
        actual = [s for s in self.aws._get_streams_from_pattern('X', 'A[AC]A')]
        self.assertEqual(actual, expected)

    def test_get_groups_from_pattern(self):
        side_effect = [
            {'logGroups': [{'logGroupName': 'AAA'},
                           {'logGroupName': 'ABA'},
                           {'logGroupName': 'ACA'}],
             'nextToken': 1},
            {'logGroups': [{'logGroupName': 'BAA'},
                           {'logGroupName': 'BBA'},
                           {'logGroupName': 'BBB'}],
             'nextToken': 2},
            {'logGroups': [{'logGroupName': 'CAC'}]},
        ]

        self.aws.connection.describe_log_groups.side_effect = side_effect
        expected = ['AAA', 'ABA', 'ACA', 'BAA', 'BBA', 'BBB', 'CAC']
        actual = [s for s in self.aws._get_groups_from_pattern('ALL')]
        self.assertEqual(actual, expected)

        self.aws.connection.describe_log_groups.side_effect = side_effect
        expected = ['AAA', 'ABA', 'ACA']
        actual = [s for s in self.aws._get_groups_from_pattern('A')]
        self.assertEqual(actual, expected)

        self.aws.connection.describe_log_groups.side_effect = side_effect
        expected = ['AAA', 'ACA']
        actual = [s for s in self.aws._get_groups_from_pattern('A[AC]A')]
        self.assertEqual(actual, expected)

    def test_get_streams_from_patterns(self):
        groups = [
            {'logGroups': [{'logGroupName': 'AAA'},
                           {'logGroupName': 'BAB'},
                           {'logGroupName': 'CCC'}]},
        ]

        streams = [
            {'logStreams': [{'logStreamName': 'ABB'},
                            {'logStreamName': 'ABC'},
                            {'logStreamName': 'ACD'}]},
            {'logStreams': [{'logStreamName': 'BBB'},
                            {'logStreamName': 'BBD'},
                            {'logStreamName': 'BBE'}]},
            {'logStreams': [{'logStreamName': 'CCC'}]},
        ]

        self.aws.connection.describe_log_groups.side_effect = groups
        self.aws.connection.describe_log_streams.side_effect = streams
        expected = [('AAA', 'ABB'), ('AAA', 'ABC')]
        actual = [s for s in self.aws._get_streams_from_patterns('A', 'AB')]
        self.assertEqual(actual, expected)

        self.aws.connection.describe_log_groups.side_effect = groups
        self.aws.connection.describe_log_streams.side_effect = streams
        expected = [('AAA', 'ABB'), ('AAA', 'ABC'), ('BAB', 'BBB'),
                    ('BAB', 'BBD'), ('BAB', 'BBE')]
        actual = [s for s in self.aws._get_streams_from_patterns('[AB]A.*', '.*B.*')]
        self.assertEqual(actual, expected)

    def test_raw_events_queue_consumer_exit_if_exhausted(self):
        self.aws.stream_status = {('A', 'B'): self.aws.EXHAUSTED}
        pool = Pool(size=1)
        pool.spawn(self.aws._raw_events_queue_consumer)
        pool.join()
        self.assertEqual(self.aws.events_queue.get(), NO_MORE_EVENTS)
        self.assertTrue(self.aws.events_queue.empty())

    def test_raw_events_queue_consumer_exit_when_exhausted(self):
        self.aws.stream_status = {('A', 'B'): self.aws.EXHAUSTED}
        self.aws.raw_events_queue.put((0, {'message': 'Hello'}))
        pool = Pool(size=1)
        pool.spawn(self.aws._raw_events_queue_consumer)
        pool.join()
        self.assertEqual(self.aws.events_queue.get(), 'Hello\n')
        self.assertEqual(self.aws.events_queue.get(), NO_MORE_EVENTS)
        self.assertTrue(self.aws.events_queue.empty())

    @patch('awslogs.core.gevent.sleep')
    @patch('awslogs.core.AWSLogs._get_min_timestamp')
    @patch('awslogs.core.AWSLogs._get_all_streams_exhausted')
    def test_raw_events_queue_consumer_waits_streams(self, _get_all_streams_exhausted, _get_min_timestamp, sleep):
        _get_min_timestamp.side_effect = [5, 5, 6, 7, 8, 9, 10]
        _get_all_streams_exhausted.side_effect = [
            False,
            False,
            False,
            False,
            False,
            True,
            True
        ]
        self.aws.stream_status = {('A', 'B'): self.aws.ACTIVE,
                                  ('A', 'C'): self.aws.EXHAUSTED}
        self.aws.raw_events_queue.put((8, {'message': 'Hello 8'}))
        self.aws.raw_events_queue.put((7, {'message': 'Hello 7'}))
        self.aws.raw_events_queue.put((9, {'message': 'Hello 9'}))
        self.aws.raw_events_queue.put((6, {'message': 'Hello 6'}))

        pool = Pool(size=1)
        pool.spawn(self.aws._raw_events_queue_consumer)
        pool.join()
        self.assertEqual(self.aws.events_queue.get(), 'Hello 6\n')
        self.assertEqual(self.aws.events_queue.get(), 'Hello 7\n')
        self.assertEqual(self.aws.events_queue.get(), 'Hello 8\n')
        self.assertEqual(self.aws.events_queue.get(), 'Hello 9\n')
        self.assertEqual(self.aws.events_queue.get(), NO_MORE_EVENTS)
        self.assertTrue(self.aws.events_queue.empty())

        self.assertEqual(sleep.call_args_list, [call(0.3), call(0.3)])

    def test_publisher_queue_consumer_with_empty_queue(self):
        self.aws.connection = Mock()
        pool = Pool(size=1)
        pool.spawn(self.aws._publisher_queue_consumer)
        pool.join()
        self.assertEqual(self.aws.connection.call_count, 0)

    def test_publisher_queue_consumer(self):
        self.aws.publishers_queue.put((0, ('group', 'stream', None)))
        self.aws.connection = Mock()
        self.aws.connection.get_log_events.side_effect = [
            {'events': [{'timestamp': 1, 'message': 'Hello 1'},
                        {'timestamp': 2, 'message': 'Hello 2'},
                        {'timestamp': 3, 'message': 'Hello 3'}]}
        ]
        pool = Pool(size=1)
        pool.spawn(self.aws._publisher_queue_consumer)
        pool.join()

        self.assertEqual(
            self.aws.raw_events_queue.get(),
            (1, {'timestamp': 1,
                 'message': 'Hello 1',
                 'stream': 'stream',
                 'group': 'group'})
        )

        self.assertEqual(
            self.aws.raw_events_queue.get(),
            (2, {'timestamp': 2,
                 'message': 'Hello 2',
                 'stream': 'stream',
                 'group': 'group'})
        )

        self.assertEqual(
            self.aws.raw_events_queue.get(),
            (3, {'timestamp': 3,
                 'message': 'Hello 3',
                 'stream': 'stream',
                 'group': 'group'})
        )

        self.assertTrue(self.aws.raw_events_queue.empty())
        self.assertTrue(self.aws.publishers_queue.empty())

    def test_publisher_queue_consumer_paginated(self):
        self.aws.publishers_queue.put((0, ('group', 'stream', None)))
        self.aws.connection = Mock()
        self.aws.connection.get_log_events.side_effect = [
            {'events': [{'timestamp': 1, 'message': 'Hello 1'},
                        {'timestamp': 2, 'message': 'Hello 2'},
                        {'timestamp': 3, 'message': 'Hello 3'}],
             'nextForwardToken': 'token'},
            {'events': [{'timestamp': 4, 'message': 'Hello 4'},
                        {'timestamp': 5, 'message': 'Hello 5'},
                        {'timestamp': 6, 'message': 'Hello 6'}]}
        ]
        pool = Pool(size=1)
        pool.spawn(self.aws._publisher_queue_consumer)
        pool.join()

        self.assertEqual(
            self.aws.raw_events_queue.get(),
            (1, {'timestamp': 1,
                 'message': 'Hello 1',
                 'stream': 'stream',
                 'group': 'group'})
        )

        self.assertEqual(
            self.aws.raw_events_queue.get(),
            (2, {'timestamp': 2,
                 'message': 'Hello 2',
                 'stream': 'stream',
                 'group': 'group'})
        )

        self.assertEqual(
            self.aws.raw_events_queue.get(),
            (3, {'timestamp': 3,
                 'message': 'Hello 3',
                 'stream': 'stream',
                 'group': 'group'})
        )

        self.assertEqual(
            self.aws.raw_events_queue.get(),
            (4, {'timestamp': 4,
                 'message': 'Hello 4',
                 'stream': 'stream',
                 'group': 'group'})
        )

        self.assertEqual(
            self.aws.raw_events_queue.get(),
            (5, {'timestamp': 5,
                 'message': 'Hello 5',
                 'stream': 'stream',
                 'group': 'group'})
        )

        self.assertEqual(
            self.aws.raw_events_queue.get(),
            (6, {'timestamp': 6,
                 'message': 'Hello 6',
                 'stream': 'stream',
                 'group': 'group'})
        )

        self.assertTrue(self.aws.raw_events_queue.empty())
        self.assertTrue(self.aws.publishers_queue.empty())

    def test_get_min_timestamp(self):
        self.assertEqual(self.aws._get_min_timestamp(), None)

        self.aws.stream_status = {('A', 'A'): AWSLogs.ACTIVE,
                                  ('B', 'B'): AWSLogs.ACTIVE,
                                  ('C', 'C'): AWSLogs.EXHAUSTED}
        self.aws.stream_max_timestamp = {
            ('A', 'A'): datetime(2015, 1, 1, 13, 30),
            ('B', 'B'): datetime(2015, 1, 1, 14, 30),
            ('C', 'C'): datetime(2015, 1, 1, 15, 30)
        }

        self.assertEqual(self.aws._get_min_timestamp(),
                         datetime(2015, 1, 1, 13, 30))

        self.aws.stream_status[('A', 'A')] = AWSLogs.EXHAUSTED
        self.assertEqual(self.aws._get_min_timestamp(),
                         datetime(2015, 1, 1, 14, 30))

        self.aws.stream_status[('B', 'B')] = AWSLogs.EXHAUSTED
        self.assertEqual(self.aws._get_min_timestamp(), None)

    def test_get_all_streams_exhausted(self):
        self.aws.stream_status = {}
        self.assertTrue(self.aws._get_all_streams_exhausted())

        self.aws.stream_status = {('A', 'A'): AWSLogs.ACTIVE,
                                  ('B', 'B'): AWSLogs.EXHAUSTED}
        self.assertFalse(self.aws._get_all_streams_exhausted())

        self.aws.stream_status = {('A', 'A'): AWSLogs.EXHAUSTED,
                                  ('B', 'B'): AWSLogs.EXHAUSTED}
        self.assertTrue(self.aws._get_all_streams_exhausted())

    @patch('awslogs.core.AWSConnection')
    @patch('sys.stdout', new_callable=StringIO)
    def test_main_get(self, mock_stdout, AWSConnection):
        instance = Mock()
        AWSConnection.return_value = instance
        logs = [
            {'events': [{'timestamp': 1, 'message': 'Hello 1'},
                        {'timestamp': 2, 'message': 'Hello 2'},
                        {'timestamp': 3, 'message': 'Hello 3'}],
             'nextForwardToken': 'token'},
            {'events': [{'timestamp': 4, 'message': 'Hello 4'},
                        {'timestamp': 5, 'message': 'Hello 5'},
                        {'timestamp': 6, 'message': 'Hello 6'}],
             'nextForwardToken': 'token'},
            {'events': []}
        ]

        groups = [
            {'logGroups': [{'logGroupName': 'AAA'},
                           {'logGroupName': 'BBB'},
                           {'logGroupName': 'CCC'}]},
        ]

        streams = [
            {'logStreams': [{'logStreamName': 'DDD'},
                            {'logStreamName': 'EEE'}]}
        ]

        instance.get_log_events.side_effect = logs
        instance.describe_log_groups.side_effect = groups
        instance.describe_log_streams.side_effect = streams

        main("awslogs get AAA DDD --no-color".split())
        self.assertEqual(
            mock_stdout.getvalue(),
            ("AAA DDD Hello 1\n"
             "AAA DDD Hello 2\n"
             "AAA DDD Hello 3\n"
             "AAA DDD Hello 4\n"
             "AAA DDD Hello 5\n"
             "AAA DDD Hello 6\n")
        )

    @patch('awslogs.core.AWSConnection')
    @patch('sys.stdout', new_callable=StringIO)
    def test_main_groups(self, mock_stdout, AWSConnection):
        instance = Mock()
        AWSConnection.return_value = instance

        groups = [
            {'logGroups': [{'logGroupName': 'AAA'},
                           {'logGroupName': 'BBB'},
                           {'logGroupName': 'CCC'}]},
        ]

        instance.describe_log_groups.side_effect = groups

        main("awslogs groups".split())
        self.assertEqual(
            mock_stdout.getvalue(),
            ("AAA\n"
             "BBB\n"
             "CCC\n")
        )

    @patch('awslogs.core.AWSConnection')
    @patch('sys.stdout', new_callable=StringIO)
    def test_main_streams(self, mock_stdout, AWSConnection):
        instance = Mock()
        AWSConnection.return_value = instance

        groups = [
            {'logGroups': [{'logGroupName': 'AAA'},
                           {'logGroupName': 'BBB'},
                           {'logGroupName': 'CCC'}]},
        ]

        streams = [
            {'logStreams': [{'logStreamName': 'DDD'},
                            {'logStreamName': 'EEE'}]}
        ]

        instance.describe_log_groups.side_effect = groups
        instance.describe_log_streams.side_effect = streams

        main("awslogs streams AAA".split())
        self.assertEqual(
            mock_stdout.getvalue(),
            ("DDD\n"
             "EEE\n")
        )



if __name__ == '__main__':
    unittest.main()
