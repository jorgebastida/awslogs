import pytest
import datetime
from freezegun import freeze_time
from awslogs import AWSLogs
from awslogs.exceptions import UnknownDateError
from botocore.compat import total_seconds
import yaml


@pytest.fixture
def awlogs():
    """Instance of AWSLogs"""
    return AWSLogs()


def iso2epoch(iso_str):
    """Convert ISO formatted string into number of seconds since 1970-01-01"""
    dt = datetime.datetime.strptime(iso_str, "%Y-%m-%d %H:%M:%S")
    return int(total_seconds(dt - datetime.datetime(1970, 1, 1)) * 1000)


"""Read test plan from YAML file
It is used later as parameters for test_happy.
"""
with open("tests/timeplan.yaml") as f:
    plan = yaml.load(f)


@freeze_time("2015-01-01 03:00:00")
@pytest.mark.parametrize("planitem", plan, ids=lambda itm: itm[1])
def test_happy(awlogs, monkeypatch, planitem):
    """Test ordinary datetime strings parsed by dateutils"""
    expected_iso, dateutil_time = planitem
    assert awlogs.parse_datetime(dateutil_time) == iso2epoch(expected_iso)


@freeze_time("1970-01-01")
def test_corners(awlogs, monkeypatch):
    """Test corner cases"""
    assert awlogs.parse_datetime('') is None
    assert awlogs.parse_datetime(None) is None

    with pytest.raises(UnknownDateError):
        awlogs.parse_datetime('???')
