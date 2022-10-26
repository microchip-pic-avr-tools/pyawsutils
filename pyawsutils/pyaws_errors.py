"""
pyawsutils specific exceptions
"""

class PyawsError(Exception):
    """
    Base class for all pyawsutils specific exceptions
    """

    def __init__(self, msg=None, code=0):
        super(PyawsError, self).__init__(msg)
        self.code = code
