class BaseAWSLogsException(Exception):

    code = 1

    def hint(self):
        return "Unknown Error."


class UnknownDateError(BaseAWSLogsException):

    code = 3

    def hint(self):
        return f"awslogs doesn't understand '{self.args[0]}' as a date."


class TooManyStreamsFilteredError(BaseAWSLogsException):

    code = 6

    def hint(self):
        return (
            f"The number of streams that match your pattern '{self.args[0]}' is '{self.args[1]}'. "
            f"AWS API limits the number of streams you can filter by to {self.args[2]}."
            "It might be helpful to you to not filter streams by any "
            "pattern and filter the output of awslogs."
        )


class NoStreamsFilteredError(BaseAWSLogsException):

    code = 7

    def hint(self):
        return (
            f"No streams match your pattern '{self.args[0]}' for the given time period."
        )
