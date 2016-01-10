"""Test actor."""


from asyncio import new_event_loop
from illume.queues.base import AsyncQueue, QueueClosed
from pytest import raises


class TestQueue:
    def test_queue_put_and_get(self):
        count = 100
        chunk_size = 10
        loop = new_event_loop()
        queue = AsyncQueue(chunk_size, loop=loop)
        results = []

        for n in range(count):
            assert loop.run_until_complete(queue.put(n))

        for n in range(chunk_size):
            for data in loop.run_until_complete(queue.get()):
                result = loop.run_until_complete(data)

                assert result in range(count)

    def test_queue_close(self):
        queue = AsyncQueue()
        loop = new_event_loop()

        queue.close()

        assert queue.closed
        assert queue.queue == None

        with raises(QueueClosed):
            loop.run_until_complete(queue.put(1))
