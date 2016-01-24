"""Test HTTP Client."""


from asyncio import new_event_loop
from http.client import HTTPResponse
from illume.clients.http import HTTPRequest
from illume.test.http import start_http_process, stop_http_process
from illume.test.http import TEST_HTTP_HOST, TEST_HTTP_PORT
from json import loads, dumps
from io import BytesIO
from pytest import fixture
from urllib.parse import urljoin


class FakeSocket:
    def __init__(self, response_buffer):
        self._file = response_buffer

    def makefile(self, *args, **kwargs):
        return self._file


def generate_url(proto="http", path=""):
    base = "{}://{}:{}".format(proto, TEST_HTTP_HOST, TEST_HTTP_PORT)

    return urljoin(base, path)


def parse_http_header(buf):
    src = FakeSocket(buf)
    resp = HTTPResponse(src)
    resp.begin()

    return dict(resp.headers)


class TestHTTPClient:
    @classmethod
    def setup_class(cls):
        cls.http_process = start_http_process()

    @classmethod
    def teardown_class(cls):
        stop_http_process(cls.http_process)

    @fixture
    def loop(cls):
        return new_event_loop()

    def test_client_init(self):
        HTTPRequest(
            "http://localhost/about",
            BytesIO()
        )

    def test_http_get(self, loop):
        url = generate_url(proto="http")
        buf = BytesIO()
        request = HTTPRequest(url, buf, loop=loop)

        loop.run_until_complete(request.perform())

        body = buf.getvalue()

        contents = loads(str(body, encoding="utf-8"))
        expected_host = "{}:{}".format(TEST_HTTP_HOST, TEST_HTTP_PORT)
        headers = parse_http_header(request.header_buffer)

        assert contents['Host'] == expected_host
        assert int(headers['Content-length']) == len(body)

    def test_http_post(self):
        pass

    def test_http_head(self):
        pass

    def test_https_get(self):
        pass

    def test_https_post(self):
        pass

    def test_https_head(self):
        pass

    def test_http_post_with_body(self):
        pass

    def test_malformed_header(self):
        pass

    def test_http_timeout(self):
        pass

    def test_max_size_cutoff(self):
        pass

    def test_header_max_size_cutoff(self):
        pass

    def test_http_get_with_additional_headers(self):
        pass

    def test_response_code_parser(self):
        pass

    def test_encode_gzip(self):
        pass

    def test_encode_deflate(self):
        pass

    def test_unicode_response(self):
        pass
