"""Request logger"""


from functools import partial
from illume import config
from illume.actor import Actor
from illume.filter.graph import EntityGraph
from illume.log import log
from time import time
from urllib.parse import urlsplit


class CrawlLogger(Actor):

    """Logs crawl data for analytics."""

    def on_init(self):
        self.entity_graph = EntityGraph(config.get("GRAPH_LOGGER_PATH"))

    async def on_message(self, message):
        log.info("Logging entity {}.".format(message))
        urls = message.get("urls", [])
        origin_url = message.get("url", None)
        now = int(time())

        if origin_url is None or len(urls) == 0:
            log.warn("Got invalid message")
            return

        origin = urlsplit(origin_url).netloc
        destinations = [urlsplit(u['url']).netloc for u in urls]

        self.entity_graph.add_entities(origin, destinations)
        log.info("Successfully logged {} entities".format(len(urls)))
