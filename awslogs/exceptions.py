class BaseAWSLogsException(Exception):
    pass


class ConnectionError(BaseAWSLogsException):
    code = 2


class UnknownDateError(BaseAWSLogsException):
    code = 3

class AccessDeniedException(BaseAWSLogsException):
    code = 4

class NoAuthHandlerFoundError(BaseAWSLogsException):
    code = 5
