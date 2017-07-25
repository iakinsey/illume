"""Unix socket queues."""


from asyncio import get_event_loop, Event, Lock, wait, open_unix_connection
from asyncio import Queue, FIRST_COMPLETED, start_unix_server, sleep
from asyncio import new_event_loop
from copy import copy
from illume import config
from illume.error import TaskComplete
from illume.queues.base import GeneratorQueue
from illume.queues.pool import PooledQueue
from illume.task import dies_on_stop_event, timeout
from illume.util import get_temp_file_name
from json import dumps, loads


class UnixSocket(GeneratorQueue):

    """
    Base unix socket class.

    Args:
        path (str): Path of unix socket.
        loop (asyncio.AbstractEventLoop): Event loop.
    """

    reader = None
    writer = None
    connect_retries = 0

    def __init__(self, path, loop, connect_retries=3):
        if loop is None:
            loop = get_event_loop()

        self.encoding_type = config.get("QUEUE_ENCODING_TYPE")
        self.ready = Event(loop=loop)
        self.stop_event = Event(loop=loop)
        self.path = path
        self.connect_retries = connect_retries
        self.loop = loop

    async def start(self):
        """Start queue."""
        if self.stop_event.is_set():
            raise QueueError("Socket already stopped.")

        self.ready.set()

        await self.run()

        if not self.stop_event.is_set():
            await self.stop()

    async def run(self):
        """
        Implementable.

        Implement this class to manage initialization logic.
        """
        raise NotImplementedError("UnixSocket.run")

    async def stop(self):
        """Stop queue."""
        await self.on_stop()
        self.ready.clear()
        self.stop_event.set()

    @dies_on_stop_event
    async def get(self):
        """Get from queue."""
        await self.ready.wait()

        payload = await self.reader.readline()

        if payload:
            data = self.decode(payload)

            return data

    @dies_on_stop_event
    async def put(self, data):
        """Put into queue."""
        await self.ready.wait()

        payload = self.encode(data)
        self.writer.write(payload)
        self.writer.write_eof()

    async def on_stop(self):
        """
        Implementable.

        Implement this class to manage on_stop event.
        """
        pass

    def encode(self, data):
        """Serialize data into JSON bytes."""
        data = dumps(data)

        return data.encode(self.encoding_type)

    def decode(self, data):
        """Deserialize data from JSON bytes."""
        data = data.decode(self.encoding_type)

        return loads(data) if data else None


class PooledUnixSocketServerQueue(PooledQueue):

    """
    Unix socket server queue.

    Args:
        path (str): Path to listen on.
        loop (asyncio.AbstractEventLoop): Event loop.
    """

    clients = None

    def __init__(self, path, loop):
        self.path = path
        self.clients = []
        self.loop = loop
        self.stop_event = Event(loop=loop)

    def start(self):
        """Start server."""
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
        """Handle a new connection."""
        client = self.get_connection(reader, writer)
        # TODO double check if a race condition exists here
        self.clients.append(client)
        await client.start()

    async def stop(self):
        """Stop server."""
        self.stop_event.set()

        for client in copy(self.clients):
            await client.close()

    def get_connection(self, reader, writer):
        """Get UnixSocketServerConnection object from reader/writer."""
        return UnixSocketServerConnection(
            self,
            self.pooled_actor,
            self.path,
            reader,
            writer,
            self.loop
        )

    def get_client(self, loop):
        """Generate client object from server parameters. Thread safe."""
        return UnixSocketClient(self.path, loop)


class UnixSocketServerConnection(UnixSocket):

    """
    Single connection instance from PooledUnixSocketServerQueue.

    Args:
        server (illume.queues.unix.PooledUnixSocketServerQueue): Server.
        pooled_actor (illume.queues.pool.PooledActor): Pooled actor.
        path (string): Path of unix socket.
        reader (asyncio.StreamReader): Reader.
        writer (asyncio.StreamWriter): Writer.
        loop (asyncio.AbstractEventLoop): Event loop.
    """

    def __init__(self, server, pooled_actor, path, reader, writer, loop):
        self.pooled_actor = pooled_actor
        self.server = server
        self.path = path
        self.reader = reader
        self.writer = writer

        super().__init__(path, loop=loop)

    async def on_stop(self):
        """Handle connection termination."""
        self.server.clients.remove(self)

    @dies_on_stop_event
    async def run(self):
        """Main read event loop."""
        while not self.stop_event.is_set():
            result = await self.get()

            if result is not None:
                await self.pooled_actor.on_message(result)


class UnixSocketClient(UnixSocket):

    """Unix socket client queue."""

    async def start(self):
        for n in range(self.connect_retries):
            try:
                await self.connect()
            except FileNotFoundError:
                await sleep(n, loop=self.loop)
            else:
                return

    async def connect(self):
        """Initialize the client."""
        self.reader, self.writer = await open_unix_connection(
            path=self.path,
            loop=self.loop
        )
        self.ready.set()

    async def stop(self):
        """Stop the client."""
        await timeout(self.writer.drain(), 1, self.loop)

    async def setup(self):
        """Set up the client."""
        if not self.ready.is_set():
            await self.start()

    async def put(self, message):
        await self.setup()
        await super().put(message)

    async def get(self):
        """Read data from the server."""
        await self.setup()
        await super().put(message)


def get_unix_pooled_actor(Actor, path=None, loop=None):
    """Helper method to create an actor in a pooled context."""
    if loop is None:
        loop = new_event_loop()

    if path is None:
        path = get_temp_file_name()

    pooled_queue = PooledUnixSocketServerQueue(path, loop)
    pooled_actor = PooledActor(Actor, pooled_queue, loop)

    return pooled_actor
