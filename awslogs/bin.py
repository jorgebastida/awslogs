from gevent import monkey
monkey.patch_all(thread=False)

import os
import sys
import signal
import argparse

import boto
from termcolor import colored

import exceptions
from core import AWSLogs


__version__ = "0.0.2"


def keyboard_signal_handler(signal, frame):
    print 'You pressed Ctrl+C!'
    sys.exit(0)

signal.signal(signal.SIGINT, keyboard_signal_handler)


def main(argv=None):

    argv = (argv or sys.argv)[1:]

    parser = argparse.ArgumentParser(usage=("%(prog)s group [ get | groups | streams ]"))

    parser.add_argument("--aws-access-key-id",
                        dest="aws_access_key_id",
                        type=unicode,
                        default=os.environ.get('AWS_ACCESS_KEY_ID', None),
                        help="aws access key id")

    parser.add_argument("--aws-secret-access-key",
                        dest="aws_secret_access_key",
                        type=unicode,
                        default=os.environ.get('AWS_SECRET_ACCESS_KEY', None),
                        help="aws secret access key")

    parser.add_argument("--aws-region",
                        dest="aws_region",
                        type=unicode,
                        default=os.environ.get('AWS_REGION', "eu-west-1"),
                        help="aws region")

    subparsers = parser.add_subparsers()

    # get
    get_parser = subparsers.add_parser('get', description='Get logs')
    get_parser.set_defaults(func="list_logs")

    get_parser.add_argument("log_group_name",
                            type=unicode,
                            default="ALL",
                            nargs='?',
                            help="log group name")

    get_parser.add_argument("log_stream_name",
                            type=unicode,
                            default="ALL",
                            nargs='?',
                            help="log stream name")

    get_parser.add_argument("--watch",
                            action='store_true',
                            dest='watch',
                            help="Pool for new log lines constantly")

    get_parser.add_argument("--no-group",
                            action='store_false',
                            dest='output_group_enabled',
                            help="Add group to the output")

    get_parser.add_argument("--no-stream",
                            action='store_false',
                            dest='output_stream_enabled',
                            help="Add stream to the output")

    get_parser.add_argument("-s", "--start",
                            type=unicode,
                            dest='start',
                            default='24h',
                            help="Start time")

    get_parser.add_argument("-e", "--end",
                            type=unicode,
                            dest='end',
                            help="End time")

    get_parser.add_argument("--no-color",
                            action='store_false',
                            dest='color_enabled',
                            help="Color output")

    # groups
    groups_parser = subparsers.add_parser('groups', description='List groups')
    groups_parser.set_defaults(func="list_groups")

    # streams
    streams_parser = subparsers.add_parser('streams', description='List streams')
    streams_parser.set_defaults(func="list_streams")
    streams_parser.add_argument("log_group_name",
                                type=unicode,
                                help="log group name")

    # Parse input
    options, args = parser.parse_known_args(argv)

    try:
        logs = AWSLogs(**vars(options))
        getattr(logs, options.func)()
    except exceptions.UnknownDateError, exc:
        sys.stderr.write(colored("awslogs doesn't understand '{0}' as a date.\n".format(exc), "red"))
        return exc.code
    except exceptions.ConnectionError, exc:
        sys.stderr.write(colored("awslogs can't connecto to AWS.\n", "red"))
        return exc.code
    except exceptions.AccessDeniedException, exc:
        sys.stderr.write(colored(exc.message, "red"))
        return exc.code
    except Exception:
        import platform
        import traceback
        options = vars(options)
        options['aws_access_key_id'] = 'SENSITIVE'
        options['aws_secret_access_key'] = 'SENSITIVE'
        sys.stderr.write("\n")
        sys.stderr.write("=" * 80)
        sys.stderr.write("\nYou've found a bug! Please, raise an issue attaching the following traceback\n")
        sys.stderr.write("https://github.com/jorgebastida/awslogs/issues/new\n")
        sys.stderr.write("-" * 80)
        sys.stderr.write("\n")
        sys.stderr.write("Version: {0}\n".format(__version__))
        sys.stderr.write("Python: {0}\n".format(sys.version))
        sys.stderr.write("boto version: {0}\n".format(boto.__version__))
        sys.stderr.write("Platform: {0}\n".format(platform.platform()))
        sys.stderr.write("Config: {0}\n".format(options))
        sys.stderr.write("Args: {0}\n\n".format(sys.argv))
        sys.stderr.write(traceback.format_exc())
        sys.stderr.write("=" * 80)
        sys.stderr.write("\n")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
