

class Error(Exception):
    """Base class for exceptions in this module."""
    pass


class MathError(Error):
    """Exception raised for errors in the input.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message):
        self.message = message


class InputError(Error):

    def __init__(self, message):
        self.message = message
