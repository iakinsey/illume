"""Miscellaneous utility functions."""

from errno import ENOENT, EEXIST
from illume.error import InsufficientMemory, AllocationValueError
from os import makedirs
from psutil import virtual_memory
from shutil import rmtree


def create_dir(path):
    """Create directory if it does not exist."""
    try:
        makedirs(path)
    except OSError as e:
        if e.errno != EEXIST:
            raise


def remove_or_ignore_dir(path):
    """Remove a directory if it exists."""
    try:
        rmtree(path)
    except OSError as e:
        if e.errno != ENOENT:
            raise


def get_available_memory():
    """Get available memory count."""
    return virtual_memory().available


def check_alloc_size(size, name=None):
    """
    Check if a byte size exceeds available virtual memory.

    Throw InsufficientMemory if size is out of bounds.
    """
    available = get_available_memory()

    if type(size) is not int:
        raise TypeError("{} is not a valid allocation value".format(size))

    if size > available:
        raise InsufficientMemory({
            "name": name,
            "size": size,
            "available": available
        })
    elif size <= 0:
        raise AllocationValueError({
            "name": name,
            "size": size,
            "available": available
        })
