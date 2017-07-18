from asyncio import get_event_loop, Event, Lock, wait, open_unix_connection
from asyncio import Queue, FIRST_COMPLETED, start_unix_server, sleep
from copy import copy
from illume import config
from illume.error import TaskComplete
from illume.queues.base import GeneratorQueue
from illume.queues.pool import PooledQueue
from illume.task import dies_on_stop_event, timeout
from illume.util import get_temp_file_name
from json import dumps, loads


class UnixSocket(GeneratorQueue):
    reader = None
    writer = None

    def __init__(self, path, loop):
        if loop is None:
            loop = get_event_loop()

        self.encoding_type = config.get("QUEUE_ENCODING_TYPE")
        self.ready = Event(loop=loop)
        self.stop_event = Event(loop=loop)
        self.path = path
        self.loop = loop

    async def start(self):
        if self.stop_event.is_set():
            raise QueueError("Socket already stopped.")

        self.ready.set()

        await self.run()

        if not self.stop_event.is_set():
            await self.stop()

    async def run(self):
        raise NotImplementedError("UnixSocket.run")

    async def stop(self):
        await self.on_stop()
        self.ready.clear()
        self.stop_event.set()

    @dies_on_stop_event
    async def get(self):
        await self.ready.wait()

        payload = await self.reader.readline()

        if payload:
            data = self.decode(payload)

            return data

    @dies_on_stop_event
    async def put(self, data):
        await self.ready.wait()

        payload = self.encode(data)
        self.writer.write(payload)
        self.writer.write_eof()

    async def on_stop(self):
        pass

    def encode(self, data):
        data = dumps(data)

        return data.encode(self.encoding_type)

    def decode(self, data):
        data = data.decode(self.encoding_type)

        return loads(data) if data else None


class PooledUnixSocketServerQueue(PooledQueue):
    clients = None

    def __init__(self, path, loop):
        self.path = path
        self.clients = []
        self.loop = loop
        self.stop_event = Event(loop=loop)

    def start(self):
        coro = start_unix_server(
            self.on_connect,
            path=self.path,
            loop=self.loop
        )

        self.loop.run_until_complete(coro)
        self.loop.run_forever()

    @dies_on_stop_event
    async def put(self, data):
        """Fan out data to all clients."""
        for client in copy(self.clients):
            await client.put(data)

    async def on_connect(self, reader, writer):
        client = self.get_connection(reader, writer)
        # TODO double check if a race condition exists here
        self.clients.append(client)
        await client.start()

    async def stop(self):
        self.stop_event.set()

        for client in copy(self.clients):
            await client.close()

    def get_connection(self, reader, writer):
        return UnixSocketServerConnection(
            self,
            self.pooled_actor,
            self.path,
            reader,
            writer,
            self.loop
        )

    def get_client(self, loop):
        return UnixSocketClient(self.path, loop)


class UnixSocketServerConnection(UnixSocket):
    def __init__(self, server, pooled_actor, path, reader, writer, loop):
        self.pooled_actor = pooled_actor
        self.server = server
        self.path = path
        self.reader = reader
        self.writer = writer

        super().__init__(path, loop=loop)

    async def on_stop(self):
        self.server.clients.remove(self)

    @dies_on_stop_event
    async def run(self):
        while not self.stop_event.is_set():
            result = await self.get()

            if result is not None:
                await self.pooled_actor.on_message(result)


class UnixSocketClient(UnixSocket):
    async def start(self):
        self.reader, self.writer = await open_unix_connection(
            path=self.path,
            loop=self.loop
        )
        self.ready.set()

    async def stop(self):
        await timeout(self.writer.drain(), 1, self.loop)

    async def setup(self):
        if not self.ready.is_set():
            await self.start()

    async def put(self, message):
        await self.setup()
        await super().put(message)

    async def get(self):
        await self.setup()
        await super().put(message)
