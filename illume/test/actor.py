"""Actor testing utilities."""


from illume.actor import Actor


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


def mock_actor(cls, count):
    """
    Wrap the actor so that it stops itself after n messages received.
    """

    counter = {'count': 0}

    class WrappedActor(cls):
        async def on_message(self, message):
            await super().on_message(message)

            counter['count'] += 1

            if counter['count'] == count:
                await self.stop()

    return WrappedActor
