"""Actor.

Base classes and methods for actors.
"""


from asyncio import coroutine, Queue, get_event_loop, Lock, wait, Event
from asyncio import FIRST_COMPLETED
from illume.task import get_first_completed


class Actor(object):

    """
    Main actor model.

    Args:
        inbox (GeneratorQueue): Inbox to consume from.
        outbox (GeneratorQueue): Outbox to publish to.
        loop (GeneratorQueue): Event loop.
    """

    running = False
    _force_stop = False

    def __init__(self, inbox, outbox, loop=None):
        self.inbox = inbox
        self.outbox = outbox

        if not loop:
            loop = get_event_loop()

        self._loop = loop
        self._pause_lock = Lock(loop=self._loop)
        self._stop_event = Event(loop=self._loop)
        self._test = None
        self.__testy = None

        self.on_init()

    @property
    def paused(self):
        """Indicate if actor is paused."""
        return self._pause_lock.locked()

    async def start(self):
        """Main public entry point to start the actor."""
        await self.initialize()
        await self._start()

    async def initialize(self):
        """Initialize the actor before starting."""
        await self.on_start()

        if self._force_stop:
            return

        if not self.running:
            self.running = True

    async def _start(self):
        """Run the event loop and force the on_stop event."""
        try:
            await self._run()
        finally:
            await self.on_stop()

    async def resume(self):
        """Resume the actor."""
        await self.on_resume()
        self._pause_lock.release()

    async def pause(self):
        """Pause the actor."""
        await self._pause_lock.acquire()
        await self.on_pause()

    async def _block_if_paused(self):
        """Block on the pause lock."""
        if self.paused:
            await self._pause_lock.acquire()
            await self._pause_lock.release()

    async def _run(self):
        """Main event loop."""
        while self.running:
            await self._block_if_paused()

            await self._process()

    async def publish(self, data):
        """Push data to the outbox."""
        await self.outbox.put(data)

    async def stop(self):
        """Stop the actor."""
        self.inbox = None
        self.outbox = None
        self.running = False
        self._force_stop = True

        self._stop_event.set()

        try:
            self._pause_lock.release()
        except RuntimeError:
            pass

    async def _process(self):
        """Process incoming messages."""
        if not self.inbox:
            return

        pending = {self.inbox.get(), self._stop_event.wait()}
        result = await get_first_completed(pending, self._loop)

        if self.running:
            await self.on_message(result)

    async def on_message(self, data):
        """Called when the actor receives a message."""
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
