"""Exceptions."""


class IllumeException(Exception):

    """Base exception for the application."""

    code = 0


class DatabaseCorrupt(IllumeException):

    """Database corruption detected."""

    code = 1


class QueryError(IllumeException):

    """An error occured with the query parameters specified."""

    code = 2


class BloomFilterError(IllumeException):

    """A bloom filter exception occurred."""

    code = 3


class BloomFilterSizeOverflow(IllumeException):

    """Bloom filter exceeded maximum size."""

    code = 4


class BloomFilterExceedsErrorRate(IllumeException):

    """Bloom filter exceeds desired error rate."""

    code = 5


class InsufficientMemory(IllumeException):

    """Not enough memory is available to allocate this object."""

    code = 6


class AllocationValueError(IllumeException):

    """The value provided is not a positive integer."""

    code = 7


class QueueClosed(IllumeException):

    """Can't complete operation on closed queue."""

    code = 8


class NetlocMismatch(IllumeException):

    """Domain netloc does not match url netloc."""

    code = 9


class ReadTimeout(IllumeException):

    """Socket read took too long."""

    code = 10


class ReadCutoff(IllumeException):

    """Response data too large."""

    code = 11


class FileNotFound(IllumeException):

    """File does not exist."""

    code = 12


class ParseError(IllumeException):

    """Error occurred when parsing."""

    code = 13


class QueueError(IllumeException):

    """Error occurred with queue."""

    code = 14


class NoSuchOperation(IllumeException):

    """No such operation exists."""

    code = 15
