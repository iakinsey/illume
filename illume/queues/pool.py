"""Pooled actor management."""


from illume.error import QueueError


class PooledActor:

    """
    Pooled actor.

    Allows actors to operate within a runtime controlled by a PooledQueue.

    Args:
        Actor (illume.actor.Actor): Actor class to run.
        pooled_queue (illume.queues.pool.PooledQueue): Managing queue.
        loop (asyncio.AbstractEventLoop): Event loop
    """

    outbox = None
    actor = None

    def __init__(self, Actor, pooled_queue, loop):
        self.Actor = Actor
        self.pooled_queue = pooled_queue
        self.pooled_queue.set_pooled_actor(self)
        self.loop = loop

    def set_outbox(self, outbox):
        """Set outbox of actor."""
        self.outbox = outbox

    def start(self, outbox=None):
        """Initialize pooled actor."""
        if outbox is not None:
            self.set_outbox(outbox)

        if self.outbox is None:
            err = "start was called before set_outbox in {}."
            raise QueueError(err.format(self.__class__.__name__))

        self.actor = self.Actor(self.pooled_queue, self.outbox, self.loop)
        self.pooled_queue.set_pooled_actor(self)
        self.loop.run_until_complete(self.actor.on_start())
        self.pooled_queue.init()
        self.loop.run_until_complete(self.stop())

    async def on_message(self, message):
        """Handle incoming message."""
        await self.actor.initialize()
        await self.actor.on_message(message)
        await self.actor.stop()

    async def stop(self):
        """Stop pooled actor."""
        await self.actor.on_stop()
        await self.pooled_queue.stop()


class PooledQueue:

    """
    Abstract class.

    Implement this class to create a pooled queue object that manages an Actor.
    """

    pooled_actor = None

    def set_pooled_actor(self, pooled_actor):
        """Set pooled actor."""
        self.pooled_actor = pooled_actor

    def init(self):
        """Initialize the pooled queue from PooledActor."""
        if self.pooled_actor is None:
            err = "start was called before set_pooled_actor in {}."
            raise QueueError(err.format(self.__class__.__name__))

        self.start()

    def start(self):
        """
        Implementable.

        Place logic here to initialize the pooled queue.
        """
        name = self.__class__.__name__

        raise NotImplementedError("{}.{}".format(name, "start"))

    async def stop(self):
        """
        Implementable.

        Place logic here to stop the pooled queue.
        """
        pass
