"""Test file analyzer actor."""


from asyncio import new_event_loop, Queue as AsyncIOQueue
from illume import config
from illume.test.actor import mock_actor
from illume.workers.analyzer import FileAnalyzer
from os import listdir
from os.path import join, exists
from pytest import fixture, raises, fail
from urllib.parse import urlsplit


class TestFileAnalyzer:

    """Test file analyzer actor."""

    @fixture
    def loop(self):
        return new_event_loop()

    def test_extraction(self, loop):
        test_dir = config.get("TEST_DIR")
        wiki_html_path = join(test_dir, "external", "wikipedia")

        if not exists(wiki_html_path):
            fail("Test html content folder not found.")

        paths = [
            join(wiki_html_path, i)
            for i in listdir(wiki_html_path)
            if i.endswith("html")
        ]

        if len(paths) == 0:
            fail("Test html content not found.")

        inbox = AsyncIOQueue(loop=loop)
        outbox = AsyncIOQueue(loop=loop)
        MockActor = mock_actor(FileAnalyzer, len(paths))
        actor = MockActor(inbox, outbox, loop=loop)

        async def perform():
            for path in paths:
                fd = open(path)

                fd.readline()

                url = fd.readline().split(")")[1].split()[0]
                domain = urlsplit(url).netloc

                await inbox.put({
                    "url": url,
                    "domain": domain,
                    "path": path
                })

            await actor.start()

            assert outbox.qsize() == len(paths)

            for path in paths:
                assert await outbox.get()

        loop.run_until_complete(perform())

    def test_url_parser(self):
        actor = FileAnalyzer(None, None)
        urls = [
            (
                urlsplit("http://xn--pck1ew32ihn2d.com"),
                "http://初音ミク.com/は/可愛い/です/ね?utf8=✓",
                "http://xn--pck1ew32ihn2d.com/%E3%81%AF/%E5%8F%AF%E6%84%9B%E3%81%84/%E3%81%A7%E3%81%99/%E3%81%AD?utf8=%E2%9C%93"
            ),
            (
                urlsplit("http://google.com"),
                "http://初音ミク.com/は/可愛い/です/ね?utf8=✓",
                "http://xn--pck1ew32ihn2d.com/%E3%81%AF/%E5%8F%AF%E6%84%9B%E3%81%84/%E3%81%A7%E3%81%99/%E3%81%AD?utf8=%E2%9C%93"
            ),
            (
                urlsplit("https://en.wikipedia.org/wiki/JoJo%27s_Bizarre_Adventure"),
                "/wiki/List_of_JoJo%27s_Bizarre_Adventure_characters",
                "https://en.wikipedia.org/wiki/List_of_JoJo%27s_Bizarre_Adventure_characters",
            ),
            (
                urlsplit("http://piapro.net/intl/"),
                "en.html",
                "http://piapro.net/intl/en.html"
            ),
            (
                urlsplit("http://piapro.net/intl"),
                "en.html",
                "http://piapro.net/en.html"
            ),
            (
                urlsplit("https://google.com"),
                "en.wikipedia.org/wiki",
                "http://en.wikipedia.org/wiki"
            )
        ]

        for origin_metadata, url, expected in urls:
            url, domain = actor.parse_url(origin_metadata, url)

            assert expected == url, "Parsed url should match expected"
