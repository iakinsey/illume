from illume.error import QueueError


class PooledActor:
    outbox = None

    # TODO add on_stop handler
    def __init__(self, Actor, pooled_queue, loop):
        self.Actor = Actor
        self.pooled_queue = pooled_queue
        self.pooled_queue.set_pooled_actor(self)
        self.loop = loop
        # TODO set init handler here

    def set_outbox(self, outbox):
        self.outbox = outbox

    def start(self, outbox=None):
        if outbox is not None:
            self.set_outbox(outbox)

        if self.outbox is None:
            err = "start was called before set_outbox in {}."
            raise QueueError(err.format(self.__class__.__name__))

        self.pooled_queue.set_pooled_actor(self)
        # TODO set on_start handler here
        self.pooled_queue.init()

    async def on_message(self, message):
        actor = self.Actor(self.pooled_queue, self.outbox, self.loop)

        await actor.initialize()
        await actor.on_message(message)
        await actor.stop()


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
        name = self.__class__.__name__

        raise NotImplementedError("{}.{}".format(name, "stop"))
