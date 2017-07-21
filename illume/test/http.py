"""
Test HTTP server.

See tests/test_http_client.py for more information.
"""


from http.server import HTTPServer, SimpleHTTPRequestHandler
from illume.test.error import TestFailure
from json import dumps, loads
from multiprocessing import Process, Queue
from signal import SIGKILL
from ssl import create_default_context
from os import kill
from queue import Empty
from time import sleep
from urllib.parse import urljoin


TEST_HTTP_HOST = "localhost"
TEST_HTTP_PORT = 9090
TEST_HTTPS_PORT = 9191


def generate_url(proto="http", path=""):
    base = "{}://{}:{}".format(proto, TEST_HTTP_HOST, TEST_HTTP_PORT)

    return urljoin(base, path)


class TestHTTPServer(HTTPServer):
    def __init__(self, *args, **kwargs):
        self.queue = kwargs.pop('queue')
        self.notified = False

        super().__init__(*args, **kwargs)

    def service_actions(self):
        if not self.notified and self.queue:
            self.queue.put(1)

        super().service_actions()


class TestHandler(SimpleHTTPRequestHandler):
    def dump_headers(self):
        headers = dict(self.headers)
        return_value = {"request_headers": headers}
        content_length = int(self.headers.get("Content-Length", 0))
        resp_code = int(self.headers.get("Requested-Response-Code", 200))

        self.send_response(resp_code)

        if self.command == 'POST':
            self.send_header("Was-post", 1)

            if content_length:
                content_length = int(content_length)
                request_body = self.rfile.read(content_length)
                request_body = str(request_body, encoding="utf-8")
                return_value['request_body'] = request_body
        elif self.command == 'GET':
            self.send_header("Was-get", 1)
        elif self.command == 'HEAD':
            self.send_header("Was-head", 1)

        payload = dumps(return_value).encode("latin-1")
        self.send_header("Content-length", len(payload))
        self.end_headers()
        self.wfile.write(payload)
        self.wfile.flush()

    def do_slow_request(self):
        sleep_time = int(self.headers.get('Sleep-Time', 5))

        sleep(sleep_time)
        self.dump_headers()

    def do_long_request(self):
        size = int(self.headers.get('Response-Size', 1024))
        payload = "".join(str(i) for i in range(size)).encode("latin-1")

        self.send_response(200)
        self.send_header("Content-length", len(payload))
        self.end_headers()
        self.wfile.write(payload)
        self.end_headers()

    def do_long_header(self):
        size = int(self.headers.get('Header-Size', 1024))
        payload = "{}"
        self.send_response(200)
        self.send_header("Long", "".join(str(i) for i in range(size)))
        self.end_headers()
        self.wfile.write(payload)
        self.end_headers()

    def do_invalid_header(self):
        self.wfile.write(''.join(str(i) for i in range(100)).encode('latin-1'))
        self.wfile.write(b'\r\n')

    def do_unicode_request(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        payload = "科学の限界を超えて私は来たんだよ"
        self.wfile.write(payload.encode("utf-8"))
        self.end_headers()

    def do_urls_request(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()

        counter = int(self.path.split("-")[1]) + 1

        payload = "".join("""
            <html>
                <body>
                    <a href="/urls-{}">Link</a>
                </body>
            </html>
        """.format(counter).split())
        self.wfile.write(payload.encode("utf-8"))
        self.end_headers()

    def do_GET(self):
        if self.path == '/':
            self.dump_headers()
        elif self.path == '/malformed-header':
            pass
        elif self.path == '/slow-request':
            self.do_slow_request()
        elif self.path == '/long-request':
            self.do_long_request()
        elif self.path == '/long-header':
            self.do_long_header()
        elif self.path == '/invalid-header':
            self.do_invalid_header()
        elif self.path == '/unicode-request':
            self.do_unicode_request()
        elif self.path.startswith('/urls-'):
            self.do_urls_request()

    def do_POST(self):
        self.dump_headers()

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Was-head", 1)
        self.end_headers()
        self.wfile.flush()


def start_test_http_server(host=TEST_HTTP_HOST, port=TEST_HTTP_PORT, queue=None):
    address = (host, port)
    httpd = TestHTTPServer(address, TestHandler, queue=queue)

    httpd.serve_forever()


def start_http_process(*args, **kwargs):
    queue = Queue()
    kwargs['queue'] = queue
    p = Process(target=start_test_http_server, args=args, kwargs=kwargs)
    p.daemon = True
    p.start()

    # The queue is used to assert that the http server has started.
    try:
        queue.get(timeout=4)
    except Empty:
        stop_http_process(p)
        raise TestFailure("HTTPServer never started.")

    return p


def stop_http_process(process):
    process.terminate()

    sleep(.01)

    if process.is_alive():
        kill(process.pid, SIGKILL)
