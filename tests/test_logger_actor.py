"""Test actor."""


from asyncio import new_event_loop, QueueEmpty, Queue as AsyncIOQueue
from illume import config
from illume.filter.graph import EntityGraph
from illume.test.actor import mock_actor
from illume.test.base import IllumeTest
from illume.util import  remove_or_ignore_file
from illume.workers.logger import CrawlLogger
from pytest import raises


class TestLogger(IllumeTest):
    def test_init(self):
        actor = CrawlLogger(None, None)
        assert actor.entity_graph is not None

    def test_on_message(self, loop):
        count = 100
        inbox = AsyncIOQueue(loop=loop)
        outbox = None
        MockActor = mock_actor(CrawlLogger, 1)
        actor = MockActor(inbox, outbox, loop=loop)
        url = "http://origin.com"
        urls = set("http://test{}.com".format(n) for n in range(count))
        message = {"url": url, "urls": [{"url": u} for u in urls]}

        async def perform():
            await inbox.put(message)
            await actor.start()

        loop.run_until_complete(perform())

        graph = actor.entity_graph
        cursor = graph.create_cursor()

        query = "SELECT source, target, observed FROM graph"
        cursor.execute(query)

        results = cursor.fetchall()

        assert len(results) == len(urls)

        for index, row in enumerate(results):
            source, target, observed = row

            assert ("http://" + target) in urls
            assert ("http://" + source) == url
            assert type(observed) is int
