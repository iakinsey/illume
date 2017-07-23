"""HTTP/HTTPS fetcher crawler component."""


from illume import config
from illume.actor import Actor
from illume.clients.http import HTTPRequest
from illume.error import IllumeException
from illume.log import log
from illume.util import create_dir
from os import getpid
from os.path import join
from shutil import move
from time import time
from urllib.parse import urlsplit


class HTTPFetcher(Actor):

    """HTTP fetcher actor."""

    def on_init(self):
        self.timeout = config.get("FETCHER_TIMEOUT_SECONDS")
        self.output_dir = config.get("FETCHER_OUTPUT_DIRECTORY")
        self.progress_dir = config.get("FETCHER_PROGRESS_DIR")
        self.max_response_size = config.get("FETCHER_MAX_RESPONSE_SIZE")
        self.max_header_size = config.get("FETCHER_HEADER_MAX_SIZE")
        self.shard_id = config.get("SHARD_ID")
        self.pid = getpid()
        self.sequence = 0

        create_dir(self.output_dir)
        create_dir(self.progress_dir)

    async def on_message(self, message):
        """Get URL."""
        url = message['url']
        domain = message['domain']
        method = message.get('method', "GET")
        request_body = message.get("body", None)
        add_headers = message.get("headers", None)
        file_name = self.get_unique_file_name()
        progress_path = join(self.progress_dir, file_name)
        destination_path = join(self.output_dir, file_name)
        writer = open(progress_path, 'wb')
        result = {
            "url": url,
            "domain": domain,
            "path": destination_path
        }

        client = HTTPRequest(
            url,
            writer,
            method=method,
            timeout=self.timeout,
            request_body=request_body,
            headers=add_headers,
            max_response_size=self.max_response_size,
            max_header_size=self.max_header_size,
            loop=self._loop
        )

        try:
            await client.perform()
        except IllumeException as e:
            result['success'] = False
            result['error'] = e.code
            log.error("'{}' occurred while fetching {}.".format(e, url))
        else:
            result['success'] = True
            result['md5'] = client.md5_hash
            result['http_code'] = client.response_code
            log.info("Successfully fetched {}".format(url))

        move(progress_path, destination_path)
        await self.publish(result)

    def get_unique_file_name(self):
        """Get a unique file name to store the result in."""
        self.sequence += 1

        return "fetcher-{}-{}-{}-{}".format(
            self.shard_id,
            int(time()),
            getpid(),
            self.sequence
        )
