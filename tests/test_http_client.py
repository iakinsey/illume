"""Test HTTP Client."""


from asyncio import new_event_loop
from illume.clients.http import HTTPRequest
from illume.error import ReadTimeout, ReadCutoff
from illume.test.http import start_http_process, stop_http_process
from illume.test.http import TEST_HTTP_HOST, TEST_HTTP_PORT
from json import loads, dumps
from io import BytesIO
from pytest import fixture, raises
from urllib.parse import urljoin


def generate_url(proto="http", path=""):
    base = "{}://{}:{}".format(proto, TEST_HTTP_HOST, TEST_HTTP_PORT)

    return urljoin(base, path)


class TestHTTPClient:
    @classmethod
    def setup_class(cls):
        cls.http_process = start_http_process()

    @classmethod
    def teardown_class(cls):
        stop_http_process(cls.http_process)

    @fixture
    def loop(self):
        return new_event_loop()

    @fixture
    def buf(self):
        return BytesIO()

    def test_client_init(self):
        HTTPRequest(
            "http://localhost/about",
            BytesIO()
        )

    def test_http_get(self, loop, buf):
        url = generate_url()
        request = HTTPRequest(url, buf, loop=loop)

        loop.run_until_complete(request.perform())

        body = buf.getvalue()
        contents = loads(str(body, encoding="utf-8"))
        expected_host = "{}:{}".format(TEST_HTTP_HOST, TEST_HTTP_PORT)
        headers = request.response_headers

        assert contents['request_headers']['Host'] == expected_host
        assert int(headers['Content-length']) == len(body)
        assert headers['Was-get'] == '1'

    def test_http_post(self, loop, buf):
        url = generate_url()
        request = HTTPRequest(url, buf, loop=loop, method='POST')

        loop.run_until_complete(request.perform())
        body = buf.getvalue()
        contents = loads(str(body, encoding="utf-8"))
        expected_host = "{}:{}".format(TEST_HTTP_HOST, TEST_HTTP_PORT)

        assert contents['request_headers']['Host'] == expected_host
        assert int(request.response_headers['Content-length']) == len(body)
        assert request.response_headers['Was-post'] == '1'

    def test_http_head(self, loop, buf):
        url = generate_url()
        request = HTTPRequest(url, buf, loop=loop, method='HEAD')

        loop.run_until_complete(request.perform())

        body = buf.getvalue()
        headers = request.response_headers

        assert body == b''
        assert headers['Was-head'] == '1'

    def test_http_post_with_body(self, loop, buf):
        url = generate_url()
        body = "The quick brown fox jumps over the lazy dog."
        request = HTTPRequest(url, buf, loop=loop, method="POST", request_body=body)

        loop.run_until_complete(request.perform())

        response_body = buf.getvalue()
        headers = request.response_headers
        contents = loads(str(response_body, encoding="utf-8"))

        assert len(body) == int(contents['request_headers']['Content-Length'])
        assert headers['Was-post']
        assert contents['request_body'] == body

    def test_additional_headers(self, loop, buf):
        url = generate_url()
        k = "test-{}-key"
        v = "test-{}-value"
        headers = {k.format(i): v.format(i) for i in range(10)}
        request = HTTPRequest(url, buf, loop=loop, headers=headers)

        loop.run_until_complete(request.perform())

        response_body = buf.getvalue()
        resp_headers = request.response_headers
        contents = loads(str(response_body, encoding="utf-8"))

        assert resp_headers['Was-get']

        for key, value in headers.items():
            assert contents['request_headers'][key] == value

    def test_malformed_header(self):
        pass

    def test_http_timeout(self, loop, buf):
        url = generate_url(path="/slow-request")
        headers = {"Sleep-Time": 1}
        timeout = .1
        request = HTTPRequest(url, buf, loop=loop, headers=headers, timeout=timeout)

        with raises(ReadTimeout):
            loop.run_until_complete(request.perform())

    def test_max_size_cutoff(self, loop, buf):
        url = generate_url(path="/long-request")
        headers = {"Response-Size": 1024}
        max_size = 128
        request = HTTPRequest(url, buf, loop=loop, headers=headers, max_response_size=max_size)

        with raises(ReadCutoff):
            loop.run_until_complete(request.perform())

    def test_header_max_size_cutoff(self, loop, buf):
        url = generate_url(path="/long-header")
        headers = {"Header-Size": 1024}
        max_size = 128
        request = HTTPRequest(url, buf, loop=loop, headers=headers, max_header_size=max_size)

        with raises(ReadCutoff):
            loop.run_until_complete(request.perform())

    def test_header_parser_valid(self, loop, buf):
        url = generate_url()

        for code in [200, 301, 412, 404, 500]:
            headers = {"Requested-Response-Code": code}
            request = HTTPRequest(url, buf, loop=loop, headers=headers)
            loop.run_until_complete(request.perform())

            assert request.response_code == code
            assert request.headers_valid
            assert int(request.response_headers['Was-get']) == 1

    def test_header_parser_invalid(self, loop, buf):
        url = generate_url(path="/invalid-header")

        request = HTTPRequest(url, buf, loop=loop)

        loop.run_until_complete(request.perform())

        assert request.headers_valid == False

    def test_unicode_response(self, loop, buf):
        url = generate_url(path="/unicode-request")

        request = HTTPRequest(url, buf, loop=loop)

        loop.run_until_complete(request.perform())
        content_type = request.response_headers['Content-Type']

        assert content_type == "text/html; charset=utf-8"
        data = buf.getvalue().decode("utf-8").strip()

        assert data == "科学の限界を超えて私は来たんだよ"
