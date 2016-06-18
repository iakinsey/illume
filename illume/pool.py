from illume.actor import Actor
from illume.error import NoSuchOperation, QueueError


# Internal pool methods
ROUTE = 0
TOGGLE_PAUSE = 1
DIE = 2
SET_COUNT = 3
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

    async def kill(self):
        pass


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

    async def on_message(self, message):
        op_code = message.get(OP_CODE_VAR_NAME, None)

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

    @admin(ROUTE)
    async def route(self, data):
        pass

    @admin(TOGGLE_PAUSE)
    async def toggle_pause(self):
        pass

    @admin(DIE)
    async def die(self):
        pass

    @admin(SET_COUNT)
    async def set_count(self, data):
        pass
