from asyncio import Queue, get_event_loop, sleep
from copy import copy
from illume.actor import Actor
from illume.error import NoSuchOperation, QueueError
from illume.warn import InvalidActorCount
from random import sample
from warnings import warn


# Internal pool methods
ROUTE = 0
TOGGLE_PAUSE = 1
DIE = 2
SET_COUNT = 3
KILL_OFF = 4
SPIN_UP = 5
OP_CODE_VAR_NAME = "op_code"


class admin:
    def __init__(self, op_code):
        self.op_code = op_code

    def __call__(self, fn):
        setattr(fn, OP_CODE_VAR_NAME, self.op_code)

        return fn


class ActorPool(Actor):
    """
    AKA ExternalPoolSupervisor.

    Allows an external process to communicate with an InternalPoolSupervisor
    process.
    """

    pid = None


class Supervisor(Actor):
    _op_map = None

    @property
    def op_map(self):
        """
        Generates a mapping between supvervisor operation codes and functions.
        """

        if self._op_map is None:
            op_map = {}

            for attr_name in dir(self):
                if attr_name == "op_map":
                    continue

                attr = getattr(self, attr_name)
                op_code = getattr(attr, OP_CODE_VAR_NAME, None)

                if op_code is not None:
                    op_map[op_code] = attr

            self._op_map = op_map

        return self._op_map

    def get_operation(self, op_code):
        fn = self.op_map.get(op_code)

        if fn is None:
            err = "No such operation exists with op_code '{}'."
            raise InvalidOperation(err.format(op_code))

        return fn

    async def call_operation(self, op_code, *args, **kwargs):
        # TODO match keyword arguments
        fn = self.get_operation(op_code)
        result = await fn(*args, **kwargs)

        return result


class InternalPoolSupervisor(Supervisor):
    """
    Sits in the same process as the actors, routes messages to the main queue
    that all actors in the pool listen to.

    This process listens to an administrative inbox.
    """

    paused = False

    def __init__(self, ActorCls, count, inbox, outbox, loop=None):
        self.Actor = ActorCls
        self.count = count
        self._loop = loop
        self.actors = {}
        self.spawned = 0
        self.active = 0
        self.stop_lock = Lock(loop=self._loop)

        super(InternalPoolSupervisor, self).__init__(inbox, outbox, loop=loop)

    async def on_start(self):
        self.consolidated_inbox = Queue(loop=self._loop)
        self.consolidated_outbox = Queue(loop=self._loop)

    def spawn(self, actor_id):
        actor = self.Actor(self.inbox, self.outbox, loop=self._loop)
        actor._actor_id = actor_id
        self.actors[actor_id] = actor
        self.spawned += 1
        self.active += 1

        self._loop.create_task(actor.start())

    async def on_message(self, message):
        if type(message) is dict:
            op_code = message.get(OP_CODE_VAR_NAME, None)
        else:
            op_code = None

        if op_code is None:
            op_code = ROUTE
            data = message
        elif data not in message:
            raise QueueError("No op code or data was provided in message.")
        else:
            data = message.get("data", None)

        kwargs = {}

        if data is not None:
            kwargs['data'] = data

        await self.call_operation(op_code, **kwargs)

    async def _process(self):
        await self.manage()
        await super(InternalPoolSupervisor, self)._process()
        await sleep(1, loop=self._loop)

    async def stop(self):
        await self.stop_lock.acquire()

        for actor_id, actor in self.actors.items():
            await actor.stop()

        await super(InternalPoolSupervisor, self).stop()

        self.stop_lock.release()

    async def manage(self):
        for actor_id, actor in copy(list(self.actors.items())):
            if not actor.running:
                await self.kill_actor(actor_id)

        pending_count = self.count - self.active

        # This should never happen. But who knows?
        if pending_count < 0:
            err = "Active actor count {} exceeds maximum of {}."
            err = err.format(self.active, self.count)

            warn(err, InvalidActorCount)

            await self.kill_off(-pending_count)
        elif self.running:
            self.spin_up(pending_count)

    def spin_up(self, count):
        """Spawn a number of actors."""

        await self.stop_lock.acquire()

        for id_ in range(count):
            self.spawn(id_)

        self.stop_lock.release()

    async def kill_actor(self, id_):
        actor = self.actors[id_]

        if actor.running:
            await actor.stop()

        del self.actors[id_]
        self.active -= 1

    @admin(KILL_OFF)
    async def kill_off(self, count):
        """Kill a number of actors in the pool."""
        ids = sample(self.actors.keys(), count)

        for id_ in ids:
            await self.kill_actor(id_)

    @admin(ROUTE)
    async def route(self, data):
        await self.consolidated_inbox.put(data)

    @admin(TOGGLE_PAUSE)
    async def toggle_pause(self):
        if self.paused:
            for actor_id, actor in self.actors.items():
                if actor.paused:
                    await actor.resume()
        else:
            for actor_id, actor in self.actors.items():
                if not actor.paused:
                    await actor.pause()

        self.paused = not self.paused

    @admin(DIE)
    async def die(self):
        await self.stop()

    @admin(SET_COUNT)
    async def set_count(self, data):
        self.count = data
