"""Test base class."""


from asyncio import new_event_loop
from pytest import fixture
from unittest import TestCase


class IllumeTest:
    """
    Interface.

    All tests should inherit from this class.
    """

    @fixture
    def loop(self):
        return new_event_loop()
