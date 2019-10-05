class BaseAWSLogsException(Exception):

    code = 1

    def hint(self):
        return "Unknown Error."


class UnknownDateError(BaseAWSLogsException):

    code = 3

    def hint(self):
        return "awslogs doesn't understand '{0}' as a date.".format(self.args[0])


class TooManyStreamsFilteredError(BaseAWSLogsException):

    code = 6

    def hint(self):
        return ("The number of streams that match your pattern '{0}' is '{1}'. "
                "AWS API limits the number of streams you can filter by to {2}."
                "It might be helpful to you to not filter streams by any "
                "pattern and filter the output of awslogs.").format(*self.args)


class NoStreamsFilteredError(BaseAWSLogsException):

    code = 7

    def hint(self):
        return ("No streams match your pattern '{0}' for the given time period.").format(*self.args)


class NoRegionSpecifiedError(BaseAWSLogsException):

    code = 8

    def hint(self):
        return ("No AWS region specified")


class InvalidCredentialsError(BaseAWSLogsException):

    code = 9

    def hint(self):
        return ("Invalid or missing credentials")


class NoSuchLogGroupError(BaseAWSLogsException):

    code = 10

    def hint(self):
        return ("The specified log group '{0}' does not exist").format(*self.args)
