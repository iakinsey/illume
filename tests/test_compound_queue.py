from asyncio import new_event_loop
from illume.queues.compound import CompoundQueue
from illume.test.base import IllumeTest
from pytest import raises


class TestCompoundQueue(IllumeTest):
    ACTION_COUNT = 37

    def test_init(self, loop):
        queues = []
        queue = CompoundQueue(queues, loop=loop)

        assert queue.queues == queues
        assert queue.loop == loop
        assert queue.ready is not None
        assert queue.stop_event is not None

    def test_do_action(self):
        fn_name = "test"
        action_args = (1,)
        options = {
            "args": (fn_name, action_args),
            "action_args": action_args,
        }
        self.run_queue_action("do_action", fn_name, options)

    def test_start(self):
        self.run_queue_action("start", "start")

    def test_get(self):
        with raises(NotImplementedError):
            self.run_queue_action("get", "get")

    def test_put(self, loop):
        args = (1234,)
        options = {
            "args": args,
            "action_args": args,
            "set_ready": True,
            "loop": loop
        }
        self.run_queue_action("put", "put", options)

    def test_stop(self, loop):
        self.run_queue_action("stop", "stop")

    def run_queue_action(self, name, action_name, options=None):
        options = options or {}
        args = options.get("args", ())
        action_args = options.get("action_args", ())
        set_ready = options.get("set_ready", False)
        loop = options.get("loop", new_event_loop())

        class MockQueue:
            async def mock_action(self, *a):
                if len(a) > 0:
                    results[self] = a
                else:
                    results[self] = True

        results = {}
        setattr(MockQueue, action_name, MockQueue.mock_action)
        queues = [MockQueue() for n in range(self.ACTION_COUNT)]
        queue = CompoundQueue(queues, loop=loop)
        fn = getattr(queue, name)

        if set_ready:
            queue.ready.set()

        action = fn(*args)

        loop.run_until_complete(action)

        assert len(results) > 0
        assert len(results) == len(queues)

        for value in results.values():
            if action_args:
                assert value == action_args
            else:
                assert value == True

        return results
