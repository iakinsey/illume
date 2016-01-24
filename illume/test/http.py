from http.server import HTTPServer, SimpleHTTPRequestHandler
from illume.test.error import TestFailure
from json import dumps, loads
from multiprocessing import Process, Queue
from signal import SIGKILL
from os import kill
from queue import Empty
from time import sleep


TEST_HTTP_HOST = "localhost"
TEST_HTTP_PORT = 9090


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
    def do_GET(self):
        return_value = dumps(dict(self.headers)).encode("latin-1")
        self.send_response(200)
        self.send_header("Content-length", len(return_value))
        self.end_headers()
        self.wfile.write(return_value)
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
