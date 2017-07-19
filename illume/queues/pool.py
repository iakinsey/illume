from illume.error import QueueError


class PooledActor:
    outbox = None
    actor = None

    def __init__(self, Actor, pooled_queue, loop):
        self.Actor = Actor
        self.pooled_queue = pooled_queue
        self.pooled_queue.set_pooled_actor(self)
        self.loop = loop

    def set_outbox(self, outbox):
        self.outbox = outbox

    def start(self, outbox=None):
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
        await self.actor.initialize()
        await self.actor.on_message(message)
        await self.actor.stop()

    async def stop(self):
        await self.actor.on_stop()
        await self.pooled_queue.stop()


class PooledQueue:
    pooled_actor = None

    # TODO remove this
    def set_pooled_actor(self, pooled_actor):
        self.pooled_actor = pooled_actor

    def init(self):
        if self.pooled_actor is None:
            err = "start was called before set_pooled_actor in {}."
            raise QueueError(err.format(self.__class__.__name__))

        self.start()

    def start(self):
        name = self.__class__.__name__

        raise NotImplementedError("{}.{}".format(name, "start"))

    async def stop(self):
        pass
