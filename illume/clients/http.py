"""HTTP/HTTPS client."""


from asyncio import open_connection, get_event_loop, FIRST_COMPLETED, sleep
from asyncio import wait
from functools import wraps
from hashlib import md5
from http.client import HTTPResponse, HTTPException
from illume.error import ReadTimeout, ReadCutoff, ParseError
from io import BytesIO
from urllib.parse import urlsplit


CRLF_LINE = b'\r\n'


class FakeSocket:

    """Mock socket used to parse an http response in parse_http_response."""

    def __init__(self, response_buffer):
        self._file = response_buffer

    def makefile(self, *args, **kwargs):
        return self._file


def parse_http_response(buf):
    """Get parsed HTTP response from request buffer."""
    src = FakeSocket(buf)
    resp = HTTPResponse(src)
    resp.begin()

    return resp


class header_property:

    """Raise exception from response if property is accessed."""

    def __init__(self, raises):
        self.raises = raises

    def __call__(self, fn):
        data = {}

        @wraps(fn)
        def func(cls, *args, **kwargs):
            success, val = cls._get_header_state()

            if not success and self.raises:
                raise val

            data['val'] = fn(cls, *args, **kwargs)

            return data['val']

        return property(func)


class HTTPRequest:

    """
    Represents a single HTTP transaction.

    Args:
        url (str): Request URL
        writer (fd): Output file descriptor
        method (str): HTTP request method
        timeout (int): Request timeout
        max_response_size (int): Max body size
        max_header_size (int): Max header size
        request_body (str): HTTP request body
        headers (dict): Request headers
        loop (asyncio.AbstractEventLoop): Event loop
    """

    _header_state = None

    def __init__(
        self,
        url,
        writer,
        method="GET",
        timeout=10,
        max_response_size=1048576, # 1 MB
        max_header_size=8192, # 8 KB
        request_body=None,
        headers=None,
        loop=None
    ):
        self.url = url
        self.method = method
        self.writer = writer
        self.request_body = request_body or ""
        self.headers = headers
        self.timeout = timeout
        self.max_response_size = max_response_size
        self.max_header_size = max_header_size
        self._md5 = md5()
        self.header_buffer = BytesIO()

        (
            self.netloc,
            self.hostname,
            self.port,
            self.path,
            self.ssl
        ) = self.parse_url(self.url)

        if loop is None:
            self._loop = get_event_loop()
        else:
            self._loop = loop

    async def perform(self):
        """Write HTTP request to server and get response."""
        conn = open_connection(
            self.hostname,
            self.port,
            ssl=self.ssl,
            loop=self._loop
        )

        reader, writer = await conn
        writer.write(self.http_query)

        await self._perform(reader)

    async def _perform(self, reader):
        """Read HTTP response."""
        reading_header = True

        while 1:
            # TODO use sendfile
            # TODO parse headers first and get response code
            line = await self.get_bytes(reader)

            if not line:
                break
            elif reading_header:
                if line == CRLF_LINE:
                    reading_header = False
                    self.header_buffer.seek(0)

                    if self.method == 'HEAD':
                        break
                else:
                    self.header_buffer.write(line)

                if self.header_buffer.tell() >= self.max_header_size:
                    raise ReadCutoff("Header too large.")
            else:
                self._md5.update(line)
                # TODO use add_writer instead
                self.writer.write(line)

                if self.writer.tell() >= self.max_response_size:
                    raise ReadCutoff("Response body too large.")

    async def get_bytes(self, reader):
        """Read bytes from server."""
        timeout_coro = sleep(self.timeout, loop=self._loop)
        reader_coro = reader.readline()
        pending = timeout_coro, reader_coro

        done, pending = await wait(
            pending,
            return_when=FIRST_COMPLETED,
            loop=self._loop
        )

        for task in pending:
            task.cancel()

        future = done.pop()

        if future._coro == timeout_coro:
            raise ReadTimeout("HTTP Request took too long.")
        else:
            return future.result()

    @header_property(raises=True)
    def response_code(self):
        """Response code."""
        return self._response.status

    @header_property(raises=True)
    def response_headers(self):
        """Resposne headers."""
        return dict(self._response.headers)

    @header_property(raises=False)
    def headers_valid(self):
        """Indicate if headers are valid."""
        success, exc = self._get_header_state()

        return success

    def _get_header_state(self):
        """Get header validity state and request exception."""
        if self._header_state:
            return self._header_state

        self.header_buffer.seek(0)

        try:
            self._response = parse_http_response(self.header_buffer)
        except Exception as e:
            self._header_state = False, e
        else:
            self._header_state = True, self._response

        return self._header_state

    @property
    def md5_hash(self):
        """MD5 of response body."""
        return self._md5.hexdigest()

    @property
    def http_query(self):
        """Raw HTTP request sent to server."""
        return "{}\r\n\r\n{}".format(
            self.request_headers,
            self.request_body
        ).encode("latin-1")

    @property
    def request_headers(self):
        """Raw HTTP request headers."""
        headers = {
            "Host": self.netloc
        }

        if self.headers:
            headers.update(self.headers)

        if self.request_body and headers.get("Content-Length", None) is None:
            headers['Content-Length'] = len(self.request_body)

        base = "{} {} HTTP/1.0".format(self.method, self.path)
        tokens = ["{}: {}".format(k, v) for k, v in headers.items()]
        tokens.insert(0, base)

        return "\r\n".join(tokens)

    def parse_url(self, url):
        """Get metadata from URL necessary to process HTTP request."""
        split_result = urlsplit(url)
        hostname = split_result.hostname
        port = split_result.port
        scheme = split_result.scheme
        netloc = split_result.netloc
        path = split_result.path or "/"
        no_port = port is None
        ssl = scheme == "https"

        if scheme == "http" and no_port:
            port = 80
        elif scheme == "https" and no_port:
            port = 443

        if hostname is None:
            raise ParseError("No hostname specified in URL.")

        return netloc, hostname, port, path, ssl
