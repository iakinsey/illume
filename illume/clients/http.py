
"""HTTP/HTTPS client."""


from asyncio import open_connection, get_event_loop, FIRST_COMPLETED, sleep
from asyncio import wait
from hashlib import md5
from io import BytesIO
from urllib.parse import urlsplit


CRLF_LINE = b'\r\n'


class HTTPRequest:

    """
    Represents a single HTTP transaction.
    """

    def __init__(
        self,
        url,
        writer,
        method="GET",
        timeout=10,
        request_body=None,
        headers=None,
        loop=None
    ):
        self.url = url
        self.method = method
        self.writer = writer
        self.request_body = request_body
        self.headers = headers
        self.timeout = timeout
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
                else:
                    self.header_buffer.write(line)
            else:
                self._md5.update(line)
                self.writer.write(line)

    async def get_bytes(self, reader):
        timeout_coro = sleep(self.timeout)
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

    @property
    def response_code(self):
        raise NotImplementedError

    @property
    def md5_hash(self):
        return self._md5.hexdigest()

    @property
    def http_query(self):
        return "{}\r\n\r\n{}".format(
            self.request_headers,
            self.request_body
        ).encode("latin-1")

    @property
    def request_headers(self):
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

        return netloc, hostname, port, path, ssl
