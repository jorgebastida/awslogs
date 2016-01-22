from pkg_resources import get_distribution, DistributionNotFound

__version__ = None  # required for initial installation

try:
    __version__ = get_distribution("awslogs").version
except DistributionNotFound:
    __version__ == '(notfound)'
