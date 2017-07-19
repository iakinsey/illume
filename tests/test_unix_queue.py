from asyncio import StreamReader, StreamWriter, gather, new_event_loop
from illume.actor import Actor
from illume.queues.pool import PooledActor, PooledQueue
from illume.queues.unix import UnixSocket, UnixSocketServerConnection
from illume.queues.unix import PooledUnixSocketServerQueue, UnixSocketClient
from illume.test.assertions import dict_equals, check_queue, check_queue_multi
from illume.test.actor import mock_actor
from illume.test.base import IllumeTest
from illume.util import get_temp_file_name
from pytest import raises
from queue import Queue
from time import sleep
from threading import Thread


class TestUnixSocket(IllumeTest):
    def test_init(self, loop):
        path = "path"
        unix_socket = UnixSocket(path, loop)

        assert unix_socket.path == path
        assert unix_socket.loop == loop
        assert unix_socket.encoding_type is not None
        assert unix_socket.ready is not None
        assert unix_socket.stop_event is not None
        assert unix_socket.reader is None
        assert unix_socket.writer is None

    def test_encode_decode(self):
        unix_socket = UnixSocket(None, None)
        test_data = {
            "string": "a string",
            "number": 1234,
            "float": 1234.5
        }

        encode = unix_socket.encode
        decode = unix_socket.decode

        assert dict_equals(test_data, decode(encode(test_data)))

    def test_get(self, loop):
        result = 39
        result_queue = Queue()
        called_queue = Queue()
        reader = StreamReader()
        unix_socket = UnixSocket(None, loop)
        unix_socket.reader = reader

        async def readline():
            called_queue.put(True)
            return unix_socket.encode(result)

        reader.readline = readline

        async def run():
            unix_socket.ready.set()
            result = await unix_socket.get()
            result_queue.put(result)

        loop.run_until_complete(run())
        check_queue(called_queue, True)
        check_queue(result_queue, result)

    def test_put(self, loop):
        result = 39
        result_queue = Queue()
        called_write = Queue()
        called_write_eof = Queue()
        writer = StreamWriter(None, None, None, None)
        unix_socket = UnixSocket(None, loop)
        unix_socket.writer = writer

        def write(data):
            called_write.put(True)
            result_queue.put(unix_socket.decode(data))

        def write_eof():
            called_write_eof.put(True)

        writer.write = write
        writer.write_eof = write_eof

        async def run():
            unix_socket.ready.set()
            await unix_socket.put(result)

        loop.run_until_complete(run())
        check_queue(called_write, True)
        check_queue(called_write_eof, True)
        check_queue(result_queue, result)

    def test_start_and_stop(self, loop):
        called_run = Queue()
        called_on_stop = Queue()
        ready_is_set = Queue()

        class TestUnixSocket(UnixSocket):
            async def run(self):
                called_run.put(True)
                ready_is_set.put(True)

            async def on_stop(self):
                called_on_stop.put(True)

        socket = TestUnixSocket(None, loop)

        assert not socket.ready.is_set()
        assert not socket.stop_event.is_set()

        loop.run_until_complete(socket.start())

        check_queue(called_run, True)
        check_queue(called_on_stop, True)
        check_queue(ready_is_set, True)

        assert not socket.ready.is_set()
        assert socket.stop_event.is_set()

    def test_socket_that_stops_itself(self, loop):
        result_queue = Queue()

        class TestUnixSocket(UnixSocket):
            async def run(self):
                result_queue.put("called run")

                if self.ready.is_set():
                    result_queue.put("ready is set")

                if not self.stop_event.is_set():
                    result_queue.put("stop event is not set")

                await self.stop()

                if self.stop_event.is_set():
                    result_queue.put("stop event is set")

                if not self.ready.is_set():
                    result_queue.put("ready is not set")

            async def on_stop(self):
                result_queue.put("stop event called")

        socket = TestUnixSocket(None, loop)

        assert not socket.ready.is_set()
        assert not socket.stop_event.is_set()

        loop.run_until_complete(socket.start())

        check_queue_multi(result_queue, [
            "called run",
            "ready is set",
            "stop event is not set",
            "stop event called",
            "stop event is set",
            "ready is not set"
        ])

        assert not socket.ready.is_set()
        assert socket.stop_event.is_set()


class TestUnixSocketServerConnection(IllumeTest):
    def test_init(self, loop):
        path = "path"
        reader = "reader"
        writer = "writer"
        pooled_actor = "pooled actor"
        server = "server"
        conn = UnixSocketServerConnection(
            server,
            pooled_actor,
            path,
            reader,
            writer,
            loop
        )

        assert conn.server == server
        assert conn.pooled_actor == pooled_actor
        assert conn.path == path
        assert conn.reader == reader
        assert conn.writer == writer
        assert conn.loop == loop

    def test_on_stop(self, loop):
        reader = "reader"
        writer = "writer"
        path = "path"
        server = PooledUnixSocketServerQueue(path, loop)
        conn = server.get_connection(reader, writer)
        server.clients.append(conn)

        assert server.clients[0] == conn

        loop.run_until_complete(conn.on_stop())

        assert len(server.clients) == 0

    def test_start(self, loop):
        result_queue = Queue()
        pooled_queue = PooledQueue()
        server = PooledUnixSocketServerQueue(None, loop)
        result = "result"

        class TestPooledActor(PooledActor):
            async def on_message(self, message):
                ret, conn = message
                result_queue.put("on_message")
                result_queue.put(ret)
                await conn.stop()

        class TestConnection(UnixSocketServerConnection):
            async def get(self):
                result_queue.put("get")
                return (result, self)

        pooled_actor = TestPooledActor(Actor, pooled_queue, loop)
        conn = TestConnection(server, pooled_actor, None, None, None, loop)
        server.clients.append(conn)

        loop.run_until_complete(conn.start())

        check_queue_multi(result_queue, [
            "get",
            "on_message",
            result
        ])

class TestPooledUnixSocketServerQueue(IllumeTest):
    def test_init(self, loop):
        path = "path"
        queue = PooledUnixSocketServerQueue(path, loop)

        assert queue.path == path
        assert queue.loop == loop
        assert queue.clients is not None
        assert len(queue.clients) == 0

    def test_start_server_and_client(self):
        result_queue = Queue()
        server_loop = new_event_loop()
        path = get_temp_file_name()

        class Server(PooledUnixSocketServerQueue):
            async def on_connect(self, reader, writer):
                result_queue.put("on_connect")
                await self.stop()

        class Client(UnixSocketClient):
            async def start(self):
                print("starting client")
                await super().start()
                self.writer.write(b"test data")
                await self.stop()

        def run_server():
            server = Server(path, server_loop)
            server.start()

        def run_client():
            loop = new_event_loop()
            client = Client(path, loop)
            loop.run_until_complete(client.start())

        server_thread = Thread(target=run_server, daemon=True)
        client_thread = Thread(target=run_client, daemon=True)

        server_thread.start()
        client_thread.start()
        check_queue(result_queue, "on_connect")
        server_loop.stop()

    def test_put(self, loop):
        result_queue = Queue()

        class MockClient:
            async def put(self, data):
                result_queue.put(data)

        count = 100
        result = "result"
        server = PooledUnixSocketServerQueue(None, loop)
        server.clients = [MockClient()] * count

        loop.run_until_complete(server.put(result))

        check_queue_multi(result_queue, [result] * count)

    def test_on_connect(self, loop):
        result_queue = Queue()

        class MockClient:
            async def start(self):
                result_queue.put("start")

        class MockServer(PooledUnixSocketServerQueue):
            def get_connection(self, reader, writer):
                result_queue.put(reader)
                result_queue.put(writer)
                result_queue.put("get_connection")

                return MockClient()

        server = MockServer(None, loop)
        loop.run_until_complete(server.on_connect("reader", "writer"))

        check_queue_multi(result_queue, [
            "reader",
            "writer",
            "get_connection",
            "start"
        ])

    def test_get_connection(self, loop):
        path = "path"
        reader = "reader"
        writer = "writer"
        server = PooledUnixSocketServerQueue(path, loop)
        conn = server.get_connection(reader, writer)

        assert conn.server == server
        assert conn.pooled_actor == server.pooled_actor
        assert conn.path == path
        assert conn.reader == reader
        assert conn.writer == writer

    def test_on_close(self, loop):
        result_queue = Queue()
        result = "close"

        class MockClient:
            async def close(self):
                result_queue.put(result)

        count = 100
        server = PooledUnixSocketServerQueue(None, loop)
        server.clients = [MockClient()] * count
        loop.run_until_complete(server.stop())

        assert server.stop_event.is_set()
        check_queue_multi(result_queue, [result] * count)

    def test_get_client(self, loop):
        server_loop = new_event_loop()
        path = "path"
        server = PooledUnixSocketServerQueue(path, server_loop)
        client = server.get_client(loop)

        assert client.path == server.path
        assert client.loop == loop
        assert client.loop != server_loop


class TestSocketInteraction(IllumeTest):
    def test_server_client_messaging(self):
        # setup
        count = 100
        sent = "sent"
        result = "result"
        path = get_temp_file_name()
        sent_message = Queue()
        recv_message = Queue()

        class TestServerActor(Actor):
            # receive 100 messages from the server
            async def on_message(self, message):
                recv_message.put(message[result])

                if q.qsize() == count:
                    await self.inbox.stop()

        class TestClientActor(Actor):
            async def on_start(self):
                sent_message.put(sent)
                await self.publish({result: result})
                await self.stop()

        def run_server():
            server_loop = new_event_loop()
            outbox = "outbox"
            pooled_queue = PooledUnixSocketServerQueue(path, server_loop)
            pooled_actor = PooledActor(TestServerActor, pooled_queue,
                                       server_loop)

            pooled_actor.start(outbox=outbox)

        client_loop = new_event_loop()

        async def run_client():
            # send 100 messages from the client
            for i in range(count):
                client = UnixSocketClient(path, client_loop)
                actor = TestClientActor(None, client, client_loop)
                await actor.start()

        # start server
        server_thread = Thread(target=run_server, daemon=True)

        server_thread.start()

        sleep(1)

        # start 100 clients
        client_loop.run_until_complete(run_client())

        # validate that 100 messages were sent and received
        check_queue_multi(sent_message, [sent] * count)
        check_queue_multi(recv_message, [result] * count)

    def test_kill_get_after_set_stop_event(self):
        pass

    def test_actor_event_calls(self):
        pass
