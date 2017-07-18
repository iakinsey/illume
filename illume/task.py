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
    await sleep(seconds)
    raise TimeoutError()


def dies_on_stop_event(fn):
    async def func(self, *args, **kwargs):
        pending = {self.stop_event.wait(), fn(self, *args, **kwargs)}
        result = await get_first_completed(pending, self.loop)

        if self.stop_event.is_set():
            pass
            # TODO
            #raise TaskComplete("Stop event has been set.")

        return result

    return func


async def timeout(coro, seconds, loop):
    pending = {sleep_and_timeout(seconds), coro}
    result = await get_first_completed(pending, loop)

    return result


def forks(fn):
    async def func(self, *args, **kwargs):
        pass

    return func
