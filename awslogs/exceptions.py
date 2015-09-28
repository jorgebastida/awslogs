class BaseAWSLogsException(Exception):

    code = 1

    def hint(self):
        return "Unknown Error."


class ConnectionError(BaseAWSLogsException):

    code = 2

    def hint(self):
        return self.args[0]


class UnknownDateError(BaseAWSLogsException):

    code = 3

    def hint(self):
        return "awslogs doesn't understand '{0}' as a date.".format(self.args[0])


class NoAuthHandlerFoundError(BaseAWSLogsException):

    code = 5

    def hint(self):
        message = [
            self.args[0],
            "Check that you have provided valid credentials in one of the following ways:",
            "* AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables.",
            "* ~/.aws/credentials",
            "* Instance profile credentials"
        ]
        return '\n'.join(message)


class TooManyStreamsFilteredError(BaseAWSLogsException):

    code = 6

    def hint(self):
        return ("The number of streams that match your patter '{0}' is '{1}'. "
                "AWS API limits the number of streams you can filter by to {2}."
                "It might be helpful to you to not filter streams by any "
                "pattern and filter the output of awslogs.").format(*self.args)
