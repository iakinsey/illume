"""Base classes and methods for generator queues."""


from asyncio import Queue, QueueEmpty, as_completed, get_event_loop
from illume.error import QueueClosed


class GeneratorQueue:

    """Generator queue abstract class."""

    closed = False

    def __init__(self, get_size=10):
        raise NotImplementedError

    def get(self):
        raise NotImplementedError

    def put(self, data):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError


class AsyncQueue(GeneratorQueue):

    """Implements the GeneratorQueue interface using the asyncio queue."""

    def __init__(self, get_size=10, loop=None):
        self.get_size = get_size

        if not loop:
            loop = get_event_loop()

        self._loop = loop
        self.queue = Queue(loop=self._loop)

    async def get(self):
        if self.closed:
            raise QueueClosed("Can't get items from closed queue")
        tasks = [self._get_single() for n in range(self.get_size)]

        return as_completed(tasks, loop=self._loop)

    async def _get_single(self):
        return await self.queue.get()

    async def put(self, data):
        if self.closed:
            raise QueueClosed("Can't put item into closed queue.")

        await self.queue.put(data)

        return True

    def close(self):
        self.queue = None
        self.closed = True
