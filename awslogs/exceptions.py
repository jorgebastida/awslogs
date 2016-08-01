class BaseAWSLogsException(Exception):

    code = 1

    def hint(self):
        return "Unknown Error."


class UnknownDateError(BaseAWSLogsException):

    code = 3

    def hint(self):
        return "awslogs doesn't understand '{0}' as a date.".format(self.args[0])


class NoStreamsFilteredError(BaseAWSLogsException):

    code = 7

    def hint(self):
        return ("No streams match your pattern '{0}'.").format(*self.args)
