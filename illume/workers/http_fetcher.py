"""HTTP/HTTPS fetcher crawler component."""


from illume import config
from illume.actor import Actor
from illume.clients.http import HTTPClient
from illume.error import IllumeException
from illume.util import create_dir
from time import time
from urllib.parse import urlsplit
from os import getpid
from os.path import join


class HTTPFetcher(Actor):

    """HTTP fetcher actor."""

    def on_init(self):
        self.timeout = config.get("FETCHER_TIMEOUT_SECONDS")
        self.output_dir = config.get("FETCHER_OUTPUT_DIRECTORY")
        self.progress_dir = config.get("FETCHER_PROGRESS_DIR")
        self.shard_id = config.get("SHARD_ID")
        self.pid = getpid()
        self.sequence = 0

        create_dir(self.output_dir)
        create_dir(self.progress_dir)

    async def on_message(self, message):
        url = message['url']
        domain = message['domain']
        method = message.get('method', "GET")
        request_body = message.get("body", None)
        add_headers = message.get("headers", None)
        file_name = self.get_unique_file_name()
        progress_path = join(self.progress_dir, file_name)
        destination_path = join(self.output_dir, file_name)
        writer = open(progress_path)
        result = {
            "url": url,
            "domain": domain,
            "path": destination_path
        }

        client = HTTPClient(
            url,
            domain,
            writer,
            method=method,
            timeout=self.timeout,
            request_body=request_body,
            headers=add_headers,
            loop=self._loop
        )

        try:
            client.fetch()
        except IllumeException as e:
            result['success'] = False
            result['error'] = e.code
        else:
            result['success'] = True
            result['md5'] = client.md5_hash
        finally:
            result['http_code'] = client.response_code

        move(progress_path, destination_path)

        self.publish(result)

    def get_unique_file_name(self):
        self.sequence += 1

        return "fetcher-{}-{}-{}-{}".format(
            self.shard_id,
            int(time()),
            getpid(),
            self.sequence
        )
