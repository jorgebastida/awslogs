class BaseAWSLogsException(Exception):

    code = 1

    def hint(self):
        return "Unknown Error."


class ConnectionError(BaseAWSLogsException):

    code = 2

    def hint(self):
        return "awslogs can't connecto to AWS."


class UnknownDateError(BaseAWSLogsException):

    code = 3

    def hint(self):
        return "awslogs doesn't understand '{0}' as a date.".format(self.args[0])


class AccessDeniedError(BaseAWSLogsException):

    code = 4

    def hint(self):
        return self.args[0]


class NoAuthHandlerFoundError(BaseAWSLogsException):

    code = 5

    def hint(self):
        message = [
            self.args[0],
            "Check that you have provided valid credentials in one of the following ways:",
            "* AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables.",
            "* /etc/boto.cfg",
            "* ~/.boto",
            "* ~/.aws/credentials",
            "* Instance profile credentials"
        ]
        return '\n'.join(message)

class InvalidRegionError(BaseAWSLogsException):

    code = 6

    def hint(self):
        if self.args[0]:
            return "{0} is not a valid AWS region name".format(self.args[0])
        return "You need to provide a valid AWS region name using --aws-region"
