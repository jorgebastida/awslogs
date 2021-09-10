import os
import sys
import argparse

import boto3
from botocore.client import ClientError
from termcolor import colored

from . import exceptions
from .core import AWSLogs
from ._version import __version__


def main(argv=None):

    argv = (argv or sys.argv)[1:]

    parser = argparse.ArgumentParser(usage=("%(prog)s [ get | groups | streams ]"))
    parser.add_argument("--version", action="version",
                        version="%(prog)s " + __version__)

    def add_common_arguments(parser):
        parser.add_argument("--aws-access-key-id",
                            dest="aws_access_key_id",
                            type=str,
                            default=None,
                            help="aws access key id")

        parser.add_argument("--aws-secret-access-key",
                            dest="aws_secret_access_key",
                            type=str,
                            default=None,
                            help="aws secret access key")

        parser.add_argument("--aws-session-token",
                            dest="aws_session_token",
                            type=str,
                            default=None,
                            help="aws session token")

        parser.add_argument("--profile",
                            dest="aws_profile",
                            type=str,
                            default=os.environ.get('AWS_PROFILE', None),
                            help="aws profile")

        parser.add_argument("--aws-region",
                            dest="aws_region",
                            type=str,
                            default=os.environ.get('AWS_REGION', None),
                            help="aws region")

        parser.add_argument("--aws-endpoint-url",
                            dest="aws_endpoint_url",
                            type=str,
                            default=os.environ.get('AWS_ENDPOINT_URL', None),
                            help="aws endpoint url to services such localstack, fakes3, others")

    def add_date_range_arguments(parser, default_start='5m'):
        parser.add_argument("-s", "--start",
                            type=str,
                            dest='start',
                            default=default_start,
                            help="Start time (default %(default)s)")

        parser.add_argument("-e", "--end",
                            type=str,
                            dest='end',
                            help="End time")

    subparsers = parser.add_subparsers()

    # get
    get_parser = subparsers.add_parser('get', description='Get logs')
    get_parser.set_defaults(func="list_logs")
    add_common_arguments(get_parser)

    get_parser.add_argument("log_group_name",
                            type=str,
                            default="ALL",
                            nargs='?',
                            help="log group name")

    get_parser.add_argument("log_stream_name",
                            type=str,
                            default="ALL",
                            nargs='?',
                            help="log stream name")

    get_parser.add_argument("-f",
                            "--filter-pattern",
                            dest='filter_pattern',
                            help=("A valid CloudWatch Logs filter pattern to "
                                  "use for filtering the response. If not "
                                  "provided, all the events are matched."))

    get_parser.add_argument("-w",
                            "--watch",
                            action='store_true',
                            dest='watch',
                            help="Query for new log lines constantly")

    get_parser.add_argument("-i",
                            "--watch-interval",
                            dest='watch_interval',
                            type=int,
                            default=1,
                            help="Interval in seconds at which to query for new log lines")

    get_parser.add_argument("-G",
                            "--no-group",
                            action='store_false',
                            dest='output_group_enabled',
                            help="Do not display group name")

    get_parser.add_argument("-S",
                            "--no-stream",
                            action='store_false',
                            dest='output_stream_enabled',
                            help="Do not display stream name")

    get_parser.add_argument("--timestamp",
                            action='store_true',
                            dest='output_timestamp_enabled',
                            help="Add creation timestamp to the output")

    get_parser.add_argument("--ingestion-time",
                            action='store_true',
                            dest='output_ingestion_time_enabled',
                            help="Add ingestion time to the output")

    add_date_range_arguments(get_parser)

    get_parser.add_argument("--color",
                            choices=['never', 'always', 'auto'],
                            metavar='WHEN',
                            default='auto',
                            help=("When to color output. WHEN can be 'auto' "
                                  "(default if omitted), 'never', or "
                                  "'always'. With --color=auto, output is "
                                  "colored only when standard output is "
                                  "connected to a terminal."))

    get_parser.add_argument("-q",
                            "--query",
                            action="store",
                            dest="query",
                            help="JMESPath query to use in filtering the response data")

    get_parser.add_argument("-p",
                            "--stream-prefix",
                            action='store_true',
                            dest="treat_stream_as_prefix",
                            help="Treat log_stream_name as a prefix instead of as a regex")

    # groups
    groups_parser = subparsers.add_parser('groups', description='List groups')
    groups_parser.set_defaults(func="list_groups")
    add_common_arguments(groups_parser)

    groups_parser.add_argument("-p",
                               "--log-group-prefix",
                               action="store",
                               dest="log_group_prefix",
                               help="List only groups matching the prefix")

    # streams
    streams_parser = subparsers.add_parser('streams', description='List streams')
    streams_parser.set_defaults(func="list_streams")
    add_common_arguments(streams_parser)
    add_date_range_arguments(streams_parser, default_start='1h')

    streams_parser.add_argument("log_group_name",
                                type=str,
                                help="log group name")

    # Parse input
    options, args = parser.parse_known_args(argv)

    try:
        logs = AWSLogs(**vars(options))
        if not hasattr(options, 'func'):
            parser.print_help()
            return 1
        getattr(logs, options.func)()
    except ClientError as exc:
        code = exc.response['Error']['Code']
        if code in (u'AccessDeniedException', u'ExpiredTokenException'):
            hint = exc.response['Error'].get('Message', 'AccessDeniedException')
            sys.stderr.write(colored("{0}\n".format(hint), "yellow"))
            return 4
        raise
    except exceptions.BaseAWSLogsException as exc:
        sys.stderr.write(colored("{0}\n".format(exc.hint()), "red"))
        return exc.code
    except Exception:
        import platform
        import traceback
        options = vars(options)
        options['aws_access_key_id'] = 'SENSITIVE'
        options['aws_secret_access_key'] = 'SENSITIVE'
        options['aws_session_token'] = 'SENSITIVE'
        options['aws_profile'] = 'SENSITIVE'
        sys.stderr.write("\n")
        sys.stderr.write("\nYou've found a bug! Please, raise an issue attaching the following traceback\n")
        sys.stderr.write("https://github.com/jorgebastida/awslogs/issues/new\n")
        sys.stderr.write("\n")

        issue_info = "\n".join((
            "Version:       {0}".format(__version__),
            "Python:        {0}".format(sys.version),
            "boto3 version: {0}".format(boto3.__version__),
            "Platform:      {0}".format(platform.platform()),
            "Args:          {0}".format(sys.argv),
            "Config: {0}".format(options),
            "",
            traceback.format_exc(),
        ))
        sys.stderr.write(issue_info + "\n")
        return 1

    return 0
