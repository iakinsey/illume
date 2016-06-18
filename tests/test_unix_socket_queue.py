from asyncio import new_event_loop
from illume.actor import Actor
from illume.queues.ipc import UnixSocketPair, UnixSocketClient, UnixSocketServer
from illume.test.actor import mock_actor
from multiprocessing import Process, Queue
from pytest import fixture, raises, fail


class TestUnixSocketQueue:
    @fixture
    def loop(self):
        return new_event_loop()

    def test_init(self, loop):
        pair = UnixSocketPair()
        client = pair.get_client()
        server = pair.get_server()

        assert pair.path is not None
        assert client.loop is not None
        assert server.loop is not None
        assert pair.path == client.path
        assert pair.path == server.path

    def test_server(self, loop):
        message = 123
        result_queue = Queue()
        pair = UnixSocketPair()
        inbox = pair.get_server(loop=loop)
        outbox = pair.get_client(loop=loop)

        class Server(Actor):
            async def on_start(self):
                await self.publish(message)

            async def on_message(self, data):
                result_queue.put(data)

        Server = mock_actor(Server, 1)
        server = Server(inbox, outbox, loop=loop)

        async def run():
            await inbox.start()
            await server.start()

        loop.run_until_complete(run())

        assert result_queue.get() == message

    def test_messaging(self):
        key = "key"
        value = "value"
        result_queue = Queue()
        first_message = "first"
        second_message = "second"
        rounds = 1
        first_pair = UnixSocketPair()
        second_pair = UnixSocketPair()

        class FirstActor(Actor):
            async def on_start(self):
                await self.publish(first_message)

            async def on_message(self, message):
                result_queue.put((second_message, message))

        class SecondActor(Actor):
            async def on_message(self, message):
                result_queue.put((first_message, message))

                await self.publish(second_message)

        def init_actor(Actor, rounds, pair1, pair2, id_):
            loop = new_event_loop()
            Actor = mock_actor(Actor, rounds)

            if id_ == 1:
                inbox = pair1.get_server(loop=loop)
                outbox = pair2.get_client(loop=loop)
            elif id_ == 2:
                inbox = pair2.get_server(loop=loop)
                outbox = pair1.get_client(loop=loop)

            actor = Actor(inbox, outbox, loop=loop)

            loop.run_until_complete(actor.start())

        first_process = Process(
            target=init_actor,
            args=(FirstActor, rounds, first_pair, second_pair, 1)
        )
        second_process = Process(
            target=init_actor,
            args=(SecondActor, rounds, first_pair, second_pair, 2)
        )

        try:
            first_process.start()
            second_process.start()

            first_result = result_queue.get(timeout=8)

            assert first_result[0] == first_result[1]
            assert first_result[1] == first_message

            second_result = result_queue.get(timeout=8)

            assert second_result[0] == second_result[1]
            assert second_result[1] == second_message
        except:
            raise
        finally:
            if first_process.is_alive():
                first_process.terminate()

            if second_process.is_alive():
                second_process.terminate()
