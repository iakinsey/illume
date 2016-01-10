"""Actor.

Base classes and methods for actors.
"""


from asyncio import coroutine, Queue, get_event_loop, Lock


class ActorManager(object):
    """
    Take actors as input.
    Start the actors.
    Stop the actors.
    Pause the actors.
    Signal to the actors that they have received a message.
    """

    def __init__(self, actors):
        self.actors = actors

    def start(self):
        pass


class Actor(object):
    running = False

    def __init__(self, inbox, outbox, loop=None):
        self.inbox = inbox
        self.outbox = outbox

        if not loop:
            loop = get_event_loop()

        self._loop = loop
        self._pause_lock = Lock(loop=self._loop)

        self.on_init()

    @property
    def paused(self):
        return self._pause_lock.locked()

    async def _get_next(self):
        return await self.inbox.get()

    async def _get_command(self):
        return await self._command_inbox.get()

    async def start(self):
        # TODO, maybe this guy just reschedules himself every time
        # instead of running in a loop?
        await self.on_start()

        if not self.running:
            self.running = True

        try:
            await self._run()
        finally:
            #if not self._stopped_manually:
            #    await self.stop()

            await self.on_stop()

    async def resume(self):
        await self.on_resume()
        self._pause_lock.release()

    async def pause(self):
        """Pause the actor."""

        await self._pause_lock.acquire()
        await self.on_pause()

    async def _block_if_paused(self):
        if self.paused:
            await self._pause_lock.acquire()
            await self._pause_lock.release()

    async def _run(self):
        while self.running:
            self._block_if_paused()
            await self._process()

    async def publish(self, data):
        """Push data to the outbox"""
        # TODO what should we do if an actor has multiple outboxes?
        # Maybe we just have composite outboxes, that would make the most sense
        # at least.

        await self.outbox.put(data)

    async def stop(self):
        """Stop the actor."""
        # TODO set a future in here or in the event loop to keep stop and
        # on_stop in sync

        #self._stopped_manually = True
        self.inbox = None
        self.outbox = None
        self.running = False

    async def _process(self):
        """Process incoming messages."""
        # TODO, what if the actor is paused and we're blocking here?
        data = await self.inbox.get()
        await self.on_message(data)

    async def on_message(self, data):
        """Called when the actor receives a message"""
        raise NotImplementedError

    def on_init(self):
        """Called after the actor class is instantiated."""
        pass

    async def on_start(self):
        """Called before the actor starts ingesting the inbox."""
        pass

    async def on_stop(self):
        """Called after actor dies."""
        pass

    async def on_pause(self):
        """Called before the actor is paused."""
        pass

    async def on_resume(self):
        """Called before the actor is resumed."""
        pass
