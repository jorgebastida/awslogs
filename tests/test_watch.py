import datetime as dt
import functools
import threading
import time
try:
    from unittest import mock
except ImportError:
    import mock

import pytest


@pytest.fixture()
def awslogs(mocker):
    from awslogs import AWSLogs

    mocker.patch('boto3.client')
    awslogs = AWSLogs(
        log_group_name='group',
        watch=True,
    )
    return awslogs


def test_watching_refresh_logs_no_stream_found(awslogs, mocker, capsys):
    """Check that a spinner is displayed when no stream are found."""

    def stop(awslogs):
        time.sleep(1.1)
        awslogs.exit.set()

    t1 = threading.Thread(target=functools.partial(stop, awslogs))
    t1.start()
    awslogs.list_logs()
    out, err = capsys.readouterr()
    assert out == 'No streams found, waiting:\n\b|\b/'


def test_watching_refresh_logs(awslogs, mocker, capsys):
    """
    Check that refresh_streams is called between WATCH_STREAM_SLEEP interval.
    """

    awslogs.WATCH_STREAM_SLEEP = .1

    awslogs._get_streams_for_list_logs = mocker.MagicMock(
        return_value=[['a']])

    def stop(awslogs):
        time.sleep(awslogs.WATCH_STREAM_SLEEP + .1)
        awslogs.exit.set()

    t1 = threading.Thread(target=functools.partial(stop, awslogs))
    t1.start()
    awslogs.list_logs()
    awslogs._get_streams_for_list_logs.assert_has_calls([mock.call()] * 3)
