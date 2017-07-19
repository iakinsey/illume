"""Test pooled actor."""


from asyncio import new_event_loop
from pytest import fixture, raises, fail
from illume.actor import Actor
from illume.error import QueueError
from illume.queues.base import GeneratorQueue
from illume.queues.pool import PooledActor, PooledQueue
from illume.test.assertions import check_queue, check_queue_multi
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
        pooled_actor = PooledActor(Actor, pooled_queue, loop)
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

    def test_pooled_actor_hooks(self, loop):
        result_queue = Queue()

        class TestQueue(GeneratorQueue):
            async def put(self, message):
                result_queue.put(message)

        class TestActor(Actor):
            def on_init(self):
                result_queue.put("on_init")

            async def on_message(self, message):
                result_queue.put(message)
                await self.publish("put")

            async def on_stop(self):
                result_queue.put("on_stop")

        class MockPooledQueue(PooledQueue):
            def start(self):
                result_queue.put("start")
                message = "on_message"
                loop.run_until_complete(self.pooled_actor.on_message(message))

            async def stop(self):
                result_queue.put("stop")

        outbox = TestQueue()
        pooled_queue = MockPooledQueue()
        pooled_actor = PooledActor(TestActor, pooled_queue, loop)
        pooled_actor.set_outbox(outbox)

        pooled_actor.start()

        check_queue_multi(result_queue, [
            "on_init",
            "start",
            "on_message",
            "put",
            "on_stop",
            "stop"
        ])
