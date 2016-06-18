"""Test actor pool."""


from asyncio import gather, new_event_loop, Queue as AsyncIOQueue
from illume import config
from illume.actor import Actor
from illume.pool import ActorPool
from illume.test.actor import mock_actor
from illume.test.http import start_http_process, stop_http_process
from pytest import fixture, raises, fail


class TestActorPool:

    """Test actor pooling."""

    @fixture
    def loop(self):
        return new_event_loop()

    def test_pool_init(self):
        return
        inbox = "inbox"
        outbox = "outbox"
        Actor = "actor"
        count = 10
        control_inbox = "control_inbox"
        control_outbox = "control_outbox"

        pool = ActorPool(
            inbox,
            outbox,
            Actor=Actor,
            count=count,
            control_inbox=control_inbox,
            control_outbox=control_outbox
        )

        assert pool.Actor == Actor
        assert pool.inbox == inbox
        assert pool.outbox == outbox
        assert pool.count == count
        assert pool.control_inbox == control_inbox
        assert pool.control_outbox == control_outbox
        assert pool._loop is not None

    def test_pool_start_and_stop(self, loop):
        return
        data = {
            "value": 0,
            "pool": None,
            "loop": loop
        }

        inbox = None
        outbox = None
        count = 100
        control_inbox = None
        control_outbox = None

        class IncrementActor(Actor):
            async def on_start(self):
                data['value'] += 1
                await self.stop()

        pool = ActorPool()

    def test_pool_pause_and_resume(self):
        pass

    def test_pool_respawn(self):
        pass

    def test_pool_message_pass(self):
        pass
