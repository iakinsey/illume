"""Queue Messenger."""


from illume.message.message import Messenger
from queue import PriorityQueue, Empty


class QueueMessenger(Messenger):

    """Implements the messenger interface with a synchronized queue."""

    def __init__(self, queue_cls=PriorityQueue):
        self._queue = queue_cls()

    def put(self, item, priority):
        self._queue.put((priority, item))

    def get(self, size=1):
        for i in range(size):
            try:
                priority, item = self._queue.get_nowait()
            except Empty:
                break
            else:
                yield item
