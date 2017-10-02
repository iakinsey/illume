"""Compound queue"""


from asyncio import wait, Event
from illume.error import QueueError
from illume.queues.base import GeneratorQueue
from illume.task import dies_on_stop_event


class CompoundQueue(GeneratorQueue):
    stop_event = None
    ready = None
    loop = None
    queues = None

    def __init__(self, queues, loop):
        self.ready = Event(loop=loop)
        self.stop_event = Event(loop=loop)
        self.queues = queues
        self.loop = loop

    async def start(self):
        if self.stop_event.is_set():
            raise QueueError("Socket already stopped.")

        await self.do_action("start")
        self.ready.set()

    @dies_on_stop_event
    async def get(self):
        raise NotImplementedError()

    @dies_on_stop_event
    async def put(self, data):
        await self.ready.wait()
        await self.do_action("put", (data,))

    async def stop(self):
        """Stop queue."""
        self.ready.clear()
        self.stop_event.set()

        await self.do_action("stop")

    async def do_action(self, name, args=()):
        coroutines = [getattr(i, name) for i in self.queues]
        tasks = [i(*args) for i in coroutines]

        await wait(tasks, loop=self.loop)
