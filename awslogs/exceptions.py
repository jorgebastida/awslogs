class BaseAWSLogsException(Exception):
    pass


class ConnectionError(BaseAWSLogsException):
    pass


class UnknownDateError(BaseAWSLogsException):
    pass
