class BaseAWSLogsException(Exception):
    pass


class ConnectionError(BaseAWSLogsException):

    code = 2


class UnknownDateError(BaseAWSLogsException):

    code = 3
