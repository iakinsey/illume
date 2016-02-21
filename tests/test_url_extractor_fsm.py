"""Test url extractor finite state machines."""


from collections import namedtuple
from illume import config
from illume.parse.link_fsm import FSM, TagReaderFsm, LinkReaderFsm
from illume.parse.link_fsm import DocumentReaderFsm
from io import StringIO
from os import listdir
from os.path import exists, join
from pytest import fail, fixture, raises


class TestUrlExtractors:
    def populate_buffer(self, contents):
        buf = StringIO()
        buf.write(contents)
        buf.seek(0)

        return buf

    def assert_fsm_test(self, FSMToTest, matcher):
        if len(matcher) == 3:
            contents, matches, expected_index = matcher
        elif len(matcher) == 2:
            contents, matches = matcher
            expected_index = None
        else:
            raise ValueError("Matcher tuple must be of length 2 or 3.")

        buf = self.populate_buffer(contents)
        fsm = FSMToTest(buf)

        fsm.perform()

        expected = set(matches)
        actual = fsm.matches

        assert len(expected) == len(actual), "Expected size should match acual."
        assert len(expected.difference(actual)) == 0
        assert len(actual.difference(expected)) == 0

        if expected_index is not None:
            assert expected_index == buf.tell()

    def perform_fsm_test(self, fsm, matches_to_test):
        for matchable in matches_to_test:
            self.assert_fsm_test(fsm, matchable)

    def test_fsm_init(self):
        # FSM can't be instantiated if `initial_state` is not set.
        with raises(NotImplementedError):
            fsm = FSM(None)

        # FSM `on_init` hook should be called.
        result = {'data': False}

        class TestFsm(FSM):
            def on_init(self):
                result['data'] = True

            @property
            def initial_state(self):
                pass

            def test_state(self):
                pass

        fsm = TestFsm(None)

        assert fsm.running == False
        assert result['data'], "Init hook was called."

    def test_tag_reader(self):
        self.perform_fsm_test(TagReaderFsm, [
            ("a href='http://google.com'>", ["http://google.com"], 26),
            ("a id='invalid'>", [], 1),
            ("a href=>", [], 7),
            ("a href=<", [], 7),
            ('div class="test">', [], 0)
        ])

    def test_link_reader(self):
        self.perform_fsm_test(LinkReaderFsm, [
            ("ttp://google.com", ["http://google.com"], 16),
            (
                'ttp://stackoverflow.com/questions/1547899/',
                ['http://stackoverflow.com/questions/1547899/'],
                42
            ),
            (
                'ttps://www.ietf.org/rfc/rfc3986.txt',
                ['https://www.ietf.org/rfc/rfc3986.txt'],
                35
            ),
            (
                'ttps://tools.ietf.org/html/rfc1738',
                ['https://tools.ietf.org/html/rfc1738'],
                34
            ),
            ("7dhjbvcxz569ij*&%$#HGVCDS", [], 0),
            ("t", [], 0),
            ("ttp", [], 3),
            ("ttp:", [], 4),
            ("ttps://", [], 7),
            ("ttp://", [], 6)
        ])

    def test_document_reader(self):
        self.perform_fsm_test(DocumentReaderFsm, [
            (
                """
                The quick brown fox jumps over the lazy dog. http://google.com
                <a href="http://piapro.net/intl/en_character.html">
                About the Piapro characters</a>
                https://en.wikipedia.org/wiki/JoJo%27s_Bizarre_Adventure
                <div class="test">Nothing of note here</div>
                <div id="thing">https://tools.ietf.org/html/rfc1738</div> More
                content here.
                """,
                [
                    "http://google.com",
                    "http://piapro.net/intl/en_character.html",
                    "https://en.wikipedia.org/wiki/JoJo%27s_Bizarre_Adventure",
                    "https://tools.ietf.org/html/rfc1738"
                ],
                434
            ),
            (
                """
                Placeholder words http://google.com <<>>
                <! <! <a id="123" href="http://piapro.net/intl/en.html>
                http://wikipedia.org
                """,
                [
                    "http://google.com",
                    "http://piapro.net/intl/en.html",
                    "http://wikipedia.org"
                ],
                167
            ),
        ])

    def test_document_reader_with_files(self):
        test_dir = config.get("TEST_DIR")
        wiki_html_path = join(test_dir, "content", "wikipedia")

        if not exists(wiki_html_path):
            fail("Test html content folder not found.")

        files = [
            open(join(wiki_html_path, i))
            for i in listdir(wiki_html_path)
            if i.endswith("html")
        ]

        if len(files) == 0:
            fail("Test html content not found.")

        for fd in files:
            fsm = DocumentReaderFsm(fd)
            fsm.perform()

            assert fsm.matches
