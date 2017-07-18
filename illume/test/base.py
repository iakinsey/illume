from asyncio import new_event_loop
from pytest import fixture
from unittest import TestCase


class IllumeTest:
    @fixture
    def loop(self):
        return new_event_loop()
