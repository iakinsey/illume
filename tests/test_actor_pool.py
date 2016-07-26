"""Test actor pool."""


from asyncio import gather, new_event_loop, Queue as AsyncIOQueue
from illume import config
from illume.actor import Actor
from illume.pool import ActorPool, InternalPoolSupervisor
from illume.test.actor import mock_actor
from illume.test.assertions import check_queue
from illume.test.http import start_http_process, stop_http_process
from pytest import fixture, raises, fail
from queue import Queue


class TestActorPool:

    """Test actor pooling."""

    @fixture
    def loop(self):
        return new_event_loop()

    def test_pool_init(self):
        inbox = "inbox"
        outbox = "outbox"
        Actor = "actor"
        count = 10
        control_inbox = "control_inbox"
        control_outbox = "control_outbox"

        pool = InternalPoolSupervisor(
            Actor,
            count,
            inbox,
            outbox,
        )

        assert pool.Actor == Actor
        assert pool.inbox == inbox
        assert pool.outbox == outbox
        assert pool.count == count
        assert pool._loop is not None

    def test_pool_start_and_stop(self, loop):
        result = {"value": 0}
        inbox = None
        outbox = None
        count = 100

        class IncrementActor(Actor):
            async def on_start(self):
                result['value'] += 1

                if result['value'] == count:
                    await result['supervisor'].stop()

                await self.stop()

        supervisor = InternalPoolSupervisor(IncrementActor, count, None, None, loop=loop)
        result['supervisor'] = supervisor

        loop.run_until_complete(supervisor.start())

        assert result['value'] == count

    def test_pool_message_pass(self, loop):
        # Create two actor pools, the first one sends a number of messages to the second.
        # The second acknowledges the messages and sends a number of responses to the first then shuts down.
        # The first acknowledges the messages then shuts down.
        count = 1
        first_result_queue = Queue()
        second_result_queue = Queue()

        first_result = 1
        second_result = 2
        metadata = {
            "first": {
                "count": 0
            },
            "second": {
                "count": 0
            },
            "A": 0
        }

        class FirstActor(Actor):
            async def on_start(self):
                await self.publish(first_result)

            async def on_message(self, data):
                second_result_queue.put(data)
                data = metadata['first']
                data['count'] += 1

                if data['count'] == count:
                    await data['pool'].stop()
                    await self.stop()

        class SecondActor(Actor):
            async def on_message(self, data):
                first_result_queue.put(data)
                await self.publish(second_result)
                data = metadata['second']
                data['count'] += 1

                if data['count'] == count:
                    await data['pool'].stop()
                    await self.stop()

        first_inbox = AsyncIOQueue(loop=loop)
        second_inbox = AsyncIOQueue(loop=loop)

        first_pool = InternalPoolSupervisor(FirstActor, count, first_inbox, second_inbox, loop=loop)
        second_pool = InternalPoolSupervisor(SecondActor, count, second_inbox, first_inbox, loop=loop)

        metadata['first']['pool'] = first_pool
        metadata['second']['pool'] = second_pool

        async def run():
            tasks = first_pool.start(), second_pool.start()
            await gather(*tasks, loop=loop)


        loop.run_until_complete(run())

        for i in range(count):
            check_queue(first_result_queue, first_result)
            check_queue(second_result_queue, second_result)

    def test_pool_admin_kill_off(self):
        pass

    def test_pool_admin_route(self):
        pass

    def test_pool_admin_toggle_pause(self):
        pass

    def test_pool_admin_die(self):
        pass

    def test_pool_admin_set_count(self):
        pass

    def test_external_pool_interface(self):
        pass
