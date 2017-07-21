"""Task-related helper methods."""


from asyncio import FIRST_COMPLETED, wait, sleep, TimeoutError


async def get_first_completed(pending, loop):
    """Return the result of the first completed task."""
    done, pending = await wait(pending, return_when=FIRST_COMPLETED,
                               loop=loop)

    for task in pending:
        task.cancel()

    future = done.pop()

    return future.result()


async def sleep_and_timeout(seconds):
    """Sleep for a number of seconds and timeout."""
    await sleep(seconds)
    raise TimeoutError()


def dies_on_stop_event(fn):
    """Kill a coroutine once the parent class's stop_event has been set."""
    async def func(self, *args, **kwargs):
        pending = {self.stop_event.wait(), fn(self, *args, **kwargs)}
        result = await get_first_completed(pending, self.loop)

        if self.stop_event.is_set():
            return None

        return result

    return func


async def timeout(coro, seconds, loop):
    """Wrapped coroutine times out after specified seconds."""
    pending = {sleep_and_timeout(seconds), coro}
    result = await get_first_completed(pending, loop)

    return result
