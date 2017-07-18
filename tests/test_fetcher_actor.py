"""Test fetcher actor."""


from asyncio import new_event_loop, Queue as AsyncIOQueue
from illume.error import ReadCutoff
from illume.test.actor import mock_actor
from illume.test.http import start_http_process, stop_http_process
from illume.test.http import generate_url, TEST_HTTP_HOST, TEST_HTTP_PORT
from illume.workers.http_fetcher import HTTPFetcher
from os.path import exists
from pytest import raises, fixture
from urllib.parse import urlsplit


class TestFetcherActor:
    @classmethod
    def setup_class(cls):
        cls.http_process = start_http_process()

    @classmethod
    def teardown_class(cls):
        stop_http_process(cls.http_process)

    @fixture
    def loop(self):
        return new_event_loop()

    def test_request_success(self, loop):
        inbox = AsyncIOQueue(loop=loop)
        outbox = AsyncIOQueue(loop=loop)
        MockActor = mock_actor(HTTPFetcher, 1)
        actor = MockActor(inbox, outbox, loop=loop)

        async def perform():
            url = generate_url()
            domain = urlsplit(url).netloc

            await inbox.put({
                "url": url,
                "domain": domain,
                "method": "GET",
            })
            await actor.start()

            result = await outbox.get()

            assert result['success']
            assert result['url'] == url
            assert result['domain'] == domain
            assert result['http_code'] == 200
            assert exists(result['path'])
            assert len(open(result['path']).read()) > 0

        loop.run_until_complete(perform())

    def test_request_fail(self, loop):
        inbox = AsyncIOQueue(loop=loop)
        outbox = AsyncIOQueue(loop=loop)
        MockActor = mock_actor(HTTPFetcher, 1)
        actor = MockActor(inbox, outbox, loop=loop)

        async def perform():
            url = generate_url(path="/long-request")
            domain = urlsplit(url).netloc
            headers = {"Response-Size": 1024}
            actor.max_response_size = 128

            await inbox.put({
                "url": url,
                "domain": domain,
                "method": "GET",
                "headers": headers
            })

            await actor.start()

            result = await outbox.get()

            assert result['success'] == False
            assert result['url'] == url
            assert result['domain'] == domain
            assert result.get("http_code", None) is None
            assert result['error'] == ReadCutoff.code
            assert exists(result['path'])
            assert len(open(result['path']).read()) > 0

        loop.run_until_complete(perform())

    def test_request_bad_response_code(self, loop):
        inbox = AsyncIOQueue(loop=loop)
        outbox = AsyncIOQueue(loop=loop)
        MockActor = mock_actor(HTTPFetcher, 1)
        actor = MockActor(inbox, outbox, loop=loop)

        async def perform():
            url = generate_url()
            domain = urlsplit(url).netloc
            http_code = 500
            headers = {"Requested-Response-Code": http_code}

            await inbox.put({
                "url": url,
                "domain": domain,
                "method": "GET",
                "headers": headers
            })

            await actor.start()

            result = await outbox.get()

            assert result['success'] == True
            assert result['url'] == url
            assert result['domain'] == domain
            assert result['http_code'] == http_code
            assert exists(result['path'])
            assert len(open(result['path']).read()) > 0

        loop.run_until_complete(perform())
