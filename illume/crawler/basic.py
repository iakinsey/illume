from asyncio import new_event_loop
from copy import copy
from illume.actor import Actor
from illume.log import log
from illume.workers.analyzer import FileAnalyzer
from illume.workers.filter import KeyFilter
from illume.workers.logger import CrawlLogger
from illume.workers.http_fetcher import HTTPFetcher
from illume.queues.compound import CompoundQueue
from illume.queues.unix import UnixSocketClient, get_unix_pooled_actor
from illume.util import get_temp_file_name
from multiprocessing import Pool
from urllib.parse import urlsplit


def catch(e):
    raise e


def _init_actor(Actor, inbox_path, outbox_ref):
    loop = new_event_loop()
    pooled_actor = get_unix_pooled_actor(Actor, inbox_path, loop)
    outbox_type = type(outbox_ref)

    if outbox_type is str:
        outbox = UnixSocketClient(outbox_ref, loop)
    elif outbox_type is tuple:
        outboxes = [UnixSocketClient(p, loop) for p in outbox_ref]
        outbox = CompoundQueue(outboxes, loop)
    else:
        raise RuntimeError("Invalid outbox type set.")

    log.info("Starting actor {}".format(Actor.__name__))
    pooled_actor.start(outbox)


class FetcherSeeder(Actor):
    seed_path = None

    @classmethod
    def init(cls, seed_path):
        cls_ = copy(cls)
        cls_.seed_path = seed_path

        return cls_

    async def on_start(self):
        if self.seed_path is None:
            raise FileNotFound("No seed path specified.")

        for line in open(self.seed_path):
            url = line.strip()
            domain = urlsplit(url).netloc
            await self.publish({
                "url": url,
                "domain": domain
            })

        await self.stop()


class BasicCrawler:
    def __init__(self, seed_path):
        self.seed_path = seed_path
        self.process_pool = Pool(4)

    def start(self):
        logger_inbox = get_temp_file_name("logger-inbox-")
        logger_outbox = get_temp_file_name("logger-outbox-")
        fetcher_inbox = get_temp_file_name("fetcher-inbox-")
        analyzer_inbox = get_temp_file_name("analyzer-inbox-")
        filter_inbox = get_temp_file_name("filter-inbox-")

        fetcher_outbox = analyzer_inbox
        analyzer_outbox = (filter_inbox, logger_inbox)
        filter_outbox = fetcher_inbox

        self.init_actor(CrawlLogger, logger_inbox, logger_outbox)
        self.init_actor(HTTPFetcher, fetcher_inbox, fetcher_outbox)
        self.init_actor(KeyFilter, filter_inbox, filter_outbox)
        self.init_actor(FileAnalyzer, analyzer_inbox, analyzer_outbox)
        self.seed_fetcher(fetcher_inbox)
        self.process_pool.close()
        self.process_pool.join()

    def init_actor(self, *args):
        self.process_pool.apply_async(_init_actor, args=args,
                                      error_callback=catch)

    def start_pool(self, pool, depends):
        loop = new_event_loop()
        pool.set_outbox(depends.get_client(loop))
        pool.start()

    def seed_fetcher(self, fetcher_inbox):
        loop = new_event_loop()
        ActorCls = FetcherSeeder.init(self.seed_path)
        outbox = UnixSocketClient(fetcher_inbox, loop)
        actor = ActorCls(None, outbox, loop=loop)

        loop.run_until_complete(actor.start())
