"""Test pooled actor."""


from asyncio import new_event_loop
from pytest import fixture, raises, fail
from illume.actor import Actor
from illume.error import QueueError
from illume.queues.pool import PooledActor, PooledQueue
from illume.test.assertions import check_queue
from queue import Queue


class TestPooledActor:
    @fixture
    def loop(self):
        return new_event_loop()

    @fixture
    def ActorCls(self):
        return Actor

    def test_pooled_actor_init(self, ActorCls, loop):
        pooled_queue = PooledQueue()
        pooled_actor = PooledActor(ActorCls, pooled_queue, loop)

        assert pooled_actor.pooled_queue == pooled_queue
        assert pooled_actor.Actor == ActorCls
        assert pooled_actor.loop == loop

    def test_pooled_queue_init(self, loop):
        result_queue = Queue()
        result = "success"
        pooled_actor = "pooled-actor"

        class MockPooledQueue(PooledQueue):
            def start(self):
                result_queue.put(result)

        pooled_queue = MockPooledQueue()

        with raises(QueueError):
            pooled_queue.init()

        pooled_queue.set_pooled_actor(pooled_actor)

        assert pooled_queue.pooled_actor == pooled_actor

        pooled_queue.init()
        check_queue(result_queue, result)

    def test_pooled_actor_set_outbox(self, loop):
        pooled_queue = PooledQueue()
        pooled_actor = PooledActor(None, pooled_queue, loop)
        outbox = "test-outbox"
        pooled_actor.set_outbox(outbox)

        assert pooled_actor.outbox == outbox

    def test_pooled_actor_start(self, loop, ActorCls):
        result_queue = Queue()
        result = "success"
        outbox = "test-outbox"

        class MockPooledQueue(PooledQueue):
            def start(self):
                result_queue.put(result)

        pooled_queue = MockPooledQueue()
        pooled_actor = PooledActor(ActorCls, pooled_queue, loop)

        # Should fail without setting the outbox.
        with raises(QueueError):
            pooled_actor.start()

        # Should succeed after setting the outbox.
        pooled_actor.set_outbox(outbox)
        pooled_actor.start()
        check_queue(result_queue, result)

    def test_pooled_actor_on_message(self, loop):
        result_queue = Queue()
        result = "success"
        outbox = "test-outbox"

        class MockActor(Actor):
            async def on_message(self, message):
                result_queue.put(message)

        class MockPooledQueue(PooledQueue):
            """
            Mimics desired interaction between PooledQueue and PooledActor.
            PooledQueue should call PooledActor.on_message.
            """
            def start(self):
                loop.run_until_complete(self.pooled_actor.on_message(result))

        pooled_queue = MockPooledQueue()
        pooled_actor = PooledActor(MockActor, pooled_queue, loop)

        pooled_actor.set_outbox(outbox)
        pooled_actor.start()
        check_queue(result_queue, result)
