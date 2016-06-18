"""IPC Queues"""


from asyncio import Future, Lock, sleep
from asyncio import open_unix_connection, start_unix_server, get_event_loop
from illume import config
from illume.error import QueueError, FileNotFound
from json import dumps, loads
from os.path import exists
from tempfile import mktemp
from uuid import uuid1


def get_temp_file_name():
    prefix = config.get("TEMP_PREFIX")
    suffix = "-{}".format(uuid1())

    return mktemp(prefix=prefix, suffix=suffix)


class UnixSocket:
    _reader = None
    _writer = None
    prepare_called = False

    def __init__(self, path, loop=None):
        if loop is None:
            loop = get_event_loop()

        self.encoding_type = config.get("QUEUE_ENCODING_TYPE")
        self.ready = Lock(loop=loop)
        self.path = path
        self.loop = loop

    async def _prepare(self):
        raise NotImplementedError("UnixSocket._prepare")

    def mark_ready(self):
        try:
            self.ready.release()
        except RuntimeError as e:
            # UGLY
            if e.__str__() != "Lock is not acquired.":
                raise

    async def prepare(self):
        await self.ready.acquire()

        if not self.prepare_called:
            self.prepare_called = True
            await self._prepare()
            await self.ready.acquire()

    async def get(self):
        await self.prepare()

        payload = await self._reader.readline()
        data = self.decode(payload)

        self.mark_ready()

        return data

    async def put(self, data):
        await self._prepare()

        payload = self.encode(data)
        self._writer.write(payload)
        self._writer.write_eof()

        self.mark_ready()

    def encode(self, data):
        data = dumps(data)

        return data.encode(self.encoding_type)

    def decode(self, data):
        data = data.decode(self.encoding_type)

        return loads(data)


class UnixSocketClient(UnixSocket):
    retries = 3
    retry_wait_start_seconds = 2

    async def _prepare(self):
        await self.socket_exists()

        self._reader, self._writer = await open_unix_connection(
            path=self.path,
            loop=self.loop
        )

        self.mark_ready()

    async def socket_exists(self):
        """
        Check if the file exists with exponential backoff and a maximum number
        of retries.
        """

        for n in range(1, self.retries + 1):
            if exists(self.path):
                return

            sleep_time = pow(self.retry_wait_start_seconds, n)
            await sleep(sleep_time, loop=self.loop)

        err = "Socket file '{}' doesn't exist."
        raise FileNotFound(err.format(self.path))

    async def get(self):
        raise QueueError("Called get() on client-side queue.")


class UnixSocketServer(UnixSocket):
    client_count = 0
    max_clients = 1

    async def _prepare(self):
        await self.__prepare()

    async def start(self):
        # TODO convert prepare_called into a lock or something.
        self.prepare_called = True
        await self.ready.acquire()
        await self.__prepare()

    async def __prepare(self):
        self.server = await start_unix_server(
            self.on_connect,
            path=self.path,
            loop=self.loop
        )

    def on_connect(self, reader, writer):
        self.client_count += 1

        if self.client_count > self.max_clients:
            err = "Too many clients ({}) connected to socket {}."
            raise QueueError(err.format(self.client_count, self.path))

        self._reader = reader
        self._writer = writer
        self.mark_ready()

    async def put(self, data):
        raise QueueError("Called put() on server-side queue")


class SocketPair:
    def get_client(self, loop=None):
        raise NotImplementedError

    def get_server(self, loop=None):
        raise NotImplementedError


class UnixSocketPair(SocketPair):

    """Allows Unix socket information to be passed across processes."""

    def __init__(self, path=None):
        if path is None:
            path = get_temp_file_name()

        self.path = path

    def get_client(self, loop=None):
        return UnixSocketClient(self.path, loop=loop)

    def get_server(self, loop=None):
        return UnixSocketServer(self.path, loop=loop)
