"""Test file analyzer actor."""


from asyncio import gather, new_event_loop, Queue as AsyncIOQueue
from illume import config
from illume.test.actor import mock_actor
from illume.test.http import start_http_process, stop_http_process
from illume.test.http import generate_url
from illume.util import  remove_or_ignore_file
from illume.workers.analyzer import FileAnalyzer
from illume.workers.filter import KeyFilter
from illume.workers.http_fetcher import HTTPFetcher
from pytest import fixture, raises, fail
from urllib.parse import urlsplit


class TestFetcherFilterAnalyzerIntegration:
    """
    Hook the fetcher, analyzer, and frontier filter actors together and test
    integration between the components.
    """

    @classmethod
    def setup_class(cls):
        cls.http_process = start_http_process()

    @classmethod
    def teardown_class(cls):
        stop_http_process(cls.http_process)

    def setup_method(self, method):
        remove_or_ignore_file(config.get("FRONTIER_KEY_FILTER_DB_PATH"))

    @fixture
    def loop(self):
        return new_event_loop()

    def test_single_message_pass(self, loop):
        Analyzer = mock_actor(FileAnalyzer, 1)
        Filter = mock_actor(KeyFilter, 1)
        Fetcher = mock_actor(HTTPFetcher, 1)
        analyzer_inbox = AsyncIOQueue(loop=loop)
        fetcher_inbox = AsyncIOQueue(loop=loop)
        filter_inbox = AsyncIOQueue(loop=loop)

        fetcher = Fetcher(fetcher_inbox, analyzer_inbox, loop=loop)
        analyzer = Analyzer(analyzer_inbox, filter_inbox, loop=loop)
        filter_ = Filter(filter_inbox, fetcher_inbox, loop=loop)
        url = generate_url(path="/")
        domain = urlsplit(url).netloc

        async def perform():
            await filter_inbox.put({
                "urls": [{
                    "url": url,
                    "domain": domain
                }]
            })

            tasks = fetcher.start(), filter_.start(), analyzer.start()

            await gather(*tasks, loop=loop)

            result = await filter_inbox.get()

            assert result['success']
            assert len(result['urls']) == 0

        loop.run_until_complete(perform())

    def test_multi_message_pass(self, loop):
        rounds = 100
        Analyzer = mock_actor(FileAnalyzer, rounds)
        Filter = mock_actor(KeyFilter, rounds)
        Fetcher = mock_actor(HTTPFetcher, rounds)
        analyzer_inbox = AsyncIOQueue(loop=loop)
        fetcher_inbox = AsyncIOQueue(loop=loop)
        filter_inbox = AsyncIOQueue(loop=loop)

        fetcher = Fetcher(fetcher_inbox, analyzer_inbox, loop=loop)
        analyzer = Analyzer(analyzer_inbox, filter_inbox, loop=loop)
        filter_ = Filter(filter_inbox, fetcher_inbox, loop=loop)
        url = generate_url(path="/urls-1")
        domain = urlsplit(url).netloc

        async def perform():
            await filter_inbox.put({
                "urls": [{
                    "url": url,
                    "domain": domain
                }]
            })

            tasks = fetcher.start(), filter_.start(), analyzer.start()

            await gather(*tasks, loop=loop)

            result = await filter_inbox.get()

            assert result['success']
            assert result['http_code'] == 200
            assert int(result['url'].split('-')[-1]) == rounds
            assert int(result['urls'][0]['url'].split('-')[-1]) == rounds + 1

        loop.run_until_complete(perform())

    def test_pooling(self, loop):
        pass

    def test_integration_with_pooling(self, loop):
        pass
