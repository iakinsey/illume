"""Test actor."""

from asyncio import new_event_loop, gather, Queue as AsyncIOQueue
from illume.actor import Actor
from illume.queues.base import AsyncQueue
from queue import Queue


def check_queue(queue, item):
    data = queue.get(timeout=1)

    assert data == item


class ActorTestable(Actor):

    """
    Actor that can be used during testing. The `running` variable switches
    whenever accessed so that the actor coroutine can return control of
    the execution context without blocking.
    """

    _running = False

    @property
    def running(self):
        self._running = not self._running

        return self._running


class TestActor:
    def test_actor_init(self):
        # Create an actor with an on_init event
        # Assert that on_init was called.

        result = {}

        class TestActor(ActorTestable):
            def on_init(self):
                result['data'] = True

        actor = TestActor(None, None)

        assert result.get("data", False)

    def test_actor_start(self):
        # Create an actor with an on_start event.
        # Assert that on_start was called.
        result = 1
        loop = new_event_loop()
        result_queue = Queue()

        class TestActor(ActorTestable):
            async def on_start(self):
                result_queue.put(result)

        inbox = AsyncQueue(loop=loop)
        actor = TestActor(inbox, None, loop=loop)

        loop.run_until_complete(actor.start())

        check_queue(result_queue, result)

    def test_actor_stop(self):
        # Create an actor with an on_stop event.
        # Assert that on_stop was called.

        result = 1
        loop = new_event_loop()
        result_queue = Queue()

        class TestActor(ActorTestable):
            async def on_stop(self):
                result_queue.put(result)

        inbox = AsyncQueue(loop=loop)
        actor = TestActor(inbox, None, loop=loop)

        loop.run_until_complete(actor.start())

        #assert actor.inbox == None
        #assert actor.outbox == None
        #assert not actor.running

        check_queue(result_queue, result)

    def test_actor_pause_and_resume(self):
        # Create an actor withon_pause and on_resume events.
        # Assert that both were called.

        loop = new_event_loop()
        pause_result = 1
        resume_result = 2
        pause_queue = Queue()
        resume_queue = Queue()

        class TestActor(ActorTestable):
            async def on_pause(self):
                pause_queue.put(pause_result)

            async def on_resume(self):
                resume_queue.put(resume_result)

            async def on_start(self):
                await self.pause()

                assert self.paused

                await self.resume()

                assert not self.paused

        inbox = AsyncQueue(loop=loop)
        actor = TestActor(inbox, None, loop=loop)

        loop.run_until_complete(actor.start())

        check_queue(pause_queue, pause_result)
        check_queue(resume_queue, resume_result)

    def test_pass_message(self):
        # Create two actors, first sends message to second, the second pauses
        # During on_pause, the second sends a message to the first indicating
        # That it's been paused
        # First then resumes second.
        # Second sends message to first to stop, first replies with stop

        first_paused_queue = Queue()
        first_stop_queue = Queue()

        second_paused_queue = Queue()
        second_resume_queue = Queue()
        second_stop_queue = Queue()

        first_paused_result = 1
        first_stop_result = 2

        second_paused_result = 3
        second_resume_result = 4
        second_stop_result = 5

        class FirstActor(Actor):
            async def on_start(self):
                await self.publish("pause")

            async def on_message(self, data):
                if data == "paused":
                    first_paused_queue.put(first_paused_result)
                    await self.publish("after_resume")
                elif data == "stop":
                    first_stop_queue.put(first_stop_result)
                    await self.publish("stop")
                    await self.stop()

        class SecondActor(Actor):
            async def on_pause(self):
                await self.resume()
                await self.publish("paused")

            async def on_message(self, data):
                if data == "pause":
                    second_paused_queue.put(second_paused_result)
                    await self.pause()
                if data =="after_resume":
                    second_resume_queue.put(second_resume_result)
                    await self.publish("stop")
                elif data == "stop":
                    second_stop_queue.put(second_stop_result)
                    await self.stop()

        loop = new_event_loop()
        first_inbox = AsyncIOQueue(loop=loop)
        second_inbox = AsyncIOQueue(loop=loop)
        first_actor = FirstActor(first_inbox, second_inbox, loop=loop)
        second_actor = SecondActor(second_inbox, first_inbox, loop=loop)

        async def run():
            tasks = first_actor.start(), second_actor.start()
            await gather(*tasks, loop=loop)

        loop.run_until_complete(run())

        check_queue(first_paused_queue, first_paused_result)
        check_queue(first_stop_queue, first_stop_result)
        check_queue(second_paused_queue, second_paused_result)
        check_queue(second_resume_queue, second_resume_result)
        check_queue(second_stop_queue, second_stop_result)
