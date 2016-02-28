import awslogs.bin
import awslogs.core
import awslogs._version


def test_versions_in_modules():
    assert awslogs.bin.__version__ == awslogs._version.__version__
