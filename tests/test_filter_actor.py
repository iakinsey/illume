"""Test actor."""


from asyncio import new_event_loop, QueueEmpty, Queue as AsyncIOQueue
from illume import config
from illume.util import  remove_or_ignore_file
from illume.workers.filter import KeyFilter
from pytest import raises


def mock_actor(cls, count):
    """
    Wrap the actor so that it stops itself after n messages received.
    """

    counter = {'count': 0}

    class WrappedActor(cls):
        async def on_message(self, message):
            await super().on_message(message)

            counter['count'] += 1

            if counter['count'] == count:
                await self.stop()

    return WrappedActor


def setup_filter(count):
    loop = new_event_loop()
    inbox = AsyncIOQueue()
    outbox = AsyncIOQueue()
    MockFilter = mock_actor(KeyFilter, count)
    key_filter = MockFilter(inbox, outbox, loop=loop)

    return loop, inbox, outbox, key_filter


class TestActor:
    def setup_method(self, method):
        remove_or_ignore_file(config.get("FRONTIER_KEY_FILTER_DB_PATH"))

    def test_filter_init(self):
        key_filter = KeyFilter(None, None)

        assert hasattr(key_filter, 'url_bloom_filter')
        assert hasattr(key_filter, 'domain_bloom_filter')
        assert hasattr(key_filter, 'persistent_key_filter')

    def test_filter_priority(self):
        loop, inbox, outbox, key_filter = setup_filter(5)
        unknown_url = "http://piapro.net/intl/en_character.html"
        known_url = "http://piapro.net/intl/en.html"
        unknown_domain = "http://google.com"
        results = {}

        async def run():
            unknown = {
                "url": unknown_url,
                "domain": "piapro.net"
            }
            known = {
                "url": known_url,
                "domain": "piapro.net"
            }
            override = {
                "url": known_url,
                "domain": "piapro.net",
                "override": True
            }
            recrawl = {
                "url": known_url,
                "domain": "piapro.net",
                "recrawl": True
            }

            await inbox.put({"urls": [unknown]})
            await inbox.put({"urls": [unknown]})
            await inbox.put({"urls": [known]})
            await inbox.put({"urls": [override]})
            await inbox.put({"urls": [recrawl]})

            await key_filter.start()

            results['unknown'] = await outbox.get()
            results['known'] = await outbox.get()
            results['override'] = await outbox.get()
            results['recrawl'] = await outbox.get()

        loop.run_until_complete(run())

        assert results['unknown']['fetch_priority'] == 2
        assert results['known']['fetch_priority'] == 3
        assert results['override']['fetch_priority'] == 1
        assert results['recrawl']['fetch_priority'] == 4

        assert results['unknown']['url'] == unknown_url
        assert results['known']['url'] == known_url
        assert results['override']['url'] == known_url
        assert results['recrawl']['url'] == known_url
