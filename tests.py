import unittest
from datetime import datetime

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

import gevent
from gevent.pool import Pool
from gevent import Greenlet

from mock import Mock, patch, call

from awslogs import AWSLogs
from awslogs.exceptions import UnknownDateError


class ShoutyGreenlet(Greenlet):

    def __init__(self, *args, **kwargs):
        super(ShoutyGreenlet, self).__init__(*args, **kwargs)
        self.link_exception(self._raise_exception)

    def _raise_exception():
        raise Exception()

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

        self.assertEqual(self.aws.parse_datetime('1m'), epoch(datetime(2015, 1, 1, 2, 59, 0, 0)))
        self.assertEqual(self.aws.parse_datetime('1m ago'), epoch(datetime(2015, 1, 1, 2, 59, 0, 0)))
        self.assertEqual(self.aws.parse_datetime('1minute'), epoch(datetime(2015, 1, 1, 2, 59, 0, 0)))
        self.assertEqual(self.aws.parse_datetime('1minute ago'), epoch(datetime(2015, 1, 1, 2, 59, 0, 0)))
        self.assertEqual(self.aws.parse_datetime('1minutes'), epoch(datetime(2015, 1, 1, 2, 59, 0, 0)))
        self.assertEqual(self.aws.parse_datetime('1minutes ago'), epoch(datetime(2015, 1, 1, 2, 59, 0, 0)))

        self.assertEqual(self.aws.parse_datetime('1h'), epoch(datetime(2015, 1, 1, 2, 0, 0, 0)))
        self.assertEqual(self.aws.parse_datetime('1h ago'), epoch(datetime(2015, 1, 1, 2, 0, 0, 0)))
        self.assertEqual(self.aws.parse_datetime('1hour'), epoch(datetime(2015, 1, 1, 2, 0, 0, 0)))
        self.assertEqual(self.aws.parse_datetime('1hour ago'), epoch(datetime(2015, 1, 1, 2, 0, 0, 0)))
        self.assertEqual(self.aws.parse_datetime('1hours'), epoch(datetime(2015, 1, 1, 2, 0, 0, 0)))
        self.assertEqual(self.aws.parse_datetime('1hours ago'), epoch(datetime(2015, 1, 1, 2, 0, 0, 0)))

        self.assertEqual(self.aws.parse_datetime('1d'), epoch(datetime(2014, 12, 31, 3, 0, 0, 0)))
        self.assertEqual(self.aws.parse_datetime('1d ago'), epoch(datetime(2014, 12, 31, 3, 0, 0, 0)))
        self.assertEqual(self.aws.parse_datetime('1day'), epoch(datetime(2014, 12, 31, 3, 0, 0, 0)))
        self.assertEqual(self.aws.parse_datetime('1day ago'), epoch(datetime(2014, 12, 31, 3, 0, 0, 0)))
        self.assertEqual(self.aws.parse_datetime('1days'), epoch(datetime(2014, 12, 31, 3, 0, 0, 0)))
        self.assertEqual(self.aws.parse_datetime('1days ago'), epoch(datetime(2014, 12, 31, 3, 0, 0, 0)))

        self.assertEqual(self.aws.parse_datetime('1w'), epoch(datetime(2014, 12, 25, 3, 0, 0, 0)))
        self.assertEqual(self.aws.parse_datetime('1w ago'), epoch(datetime(2014, 12, 25, 3, 0, 0, 0)))
        self.assertEqual(self.aws.parse_datetime('1week'), epoch(datetime(2014, 12, 25, 3, 0, 0, 0)))
        self.assertEqual(self.aws.parse_datetime('1week ago'), epoch(datetime(2014, 12, 25, 3, 0, 0, 0)))
        self.assertEqual(self.aws.parse_datetime('1weeks'), epoch(datetime(2014, 12, 25, 3, 0, 0, 0)))
        self.assertEqual(self.aws.parse_datetime('1weeks ago'), epoch(datetime(2014, 12, 25, 3, 0, 0, 0)))


        self.assertEqual(self.aws.parse_datetime('1/1/2013'), epoch(datetime(2013, 1, 1, 0, 0, 0, 0)))
        self.assertEqual(self.aws.parse_datetime('1/1/2012 12:34'), epoch(datetime(2012, 1, 1, 12, 34, 0, 0)))
        self.assertEqual(self.aws.parse_datetime('1/1/2011 12:34:56'), epoch(datetime(2011, 1, 1, 12, 34, 56, 0)))

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

    @patch('awslogs.core.sys.stdout')
    def test_event_queue_consumer(self, stdout):
        import ipdb; ipdb.set_trace()

        # Abort if EXHAUSTED
        self.aws.stream_status = {('A', 'B'): self.aws.EXHAUSTED}
        pool = Pool(size=1, greenlet_class=ShoutyGreenlet)
        pool.spawn(self.aws._event_queue_consumer)
        pool.join()
        self.assertEqual(stdout.write.call_count, 0)

        # Consume when EXHAUSTED
        self.aws.stream_status = {('A', 'B'): self.aws.EXHAUSTED}
        self.aws.events_queue.put(0, {'message': 'Hello'})
        pool = Pool(size=1, greenlet_class=ShoutyGreenlet)
        pool.spawn(self.aws._event_queue_consumer)
        pool.join()
        self.assertEqual(stdout.write.call_count, 0)


if __name__ == '__main__':
    unittest.main()
