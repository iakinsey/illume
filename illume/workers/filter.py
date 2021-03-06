"""URL/Domain filter crawler component"""


from functools import partial
from illume import config
from illume.actor import Actor
from illume.error import DatabaseCorrupt
from illume.filter.bloom import BloomFilter
from illume.filter.persistent_key_filter import PersistentKeyFilter
from illume.log import log


class KeyFilter(Actor):

    """Frontier url/domain filter actor."""

    def on_init(self):
        self.domain_whitelist = config.get("FRONTIER_DOMAIN_WHITELIST")
        self.init_bloom_filters()
        self.init_persistent_key_filter()
        self.populate_bloom_filters()

    def init_bloom_filters(self):
        """Initialize bloom filter."""
        self.url_bloom_filter = BloomFilter(
            config.get("FRONTIER_URL_BLOOM_MAX_N"),
            config.get("FRONTIER_URL_BLOOM_P")
        )

        self.domain_bloom_filter = BloomFilter(
            config.get("FRONTIER_DOMAIN_BLOOM_MAX_N"),
            config.get("FRONTIER_DOMAIN_BLOOM_P")
        )

    def init_persistent_key_filter(self):
        """Initialize persistent key filter."""
        self.key_filter_path = config.get("FRONTIER_KEY_FILTER_DB_PATH")
        self.key_filter_size = config.get("FILTER_HASHER_KEY_SIZE")
        self.persistent_key_filter = PersistentKeyFilter(
            self.key_filter_path,
            self.key_filter_size
        )
        self.cursor = self.persistent_key_filter.create_cursor()

    def populate_bloom_filters(self):
        """Populate bloom filter with data from the persistent key filter."""
        pass

    async def on_message(self, message):
        urls = message.get("urls", [])
        count = 0

        for url in urls:
            count += await self.handle_url(url)

        if count:
            log.info("{} URLS published".format(count))

    async def handle_url(self, url_map):
        """Determine if URL should be crawled."""
        url = url_map['url']
        domain = url_map['domain']
        override = url_map.get('override', False)
        recrawl = url_map.get('recrawl', False)

        if self.domain_whitelist and domain in self.domain_whitelist:
            return 0

        domain_is_known = self.exists_domain(domain)
        url_is_known = False
        should_publish = recrawl or override

        if domain_is_known:
            url_is_known = self.exists_url(domain, url)

        should_ignore = self._should_ignore(
            domain_is_known,
            url_is_known,
            override,
            recrawl
        )

        if should_ignore:
            return 0

        if not domain_is_known:
            self.domain_bloom_filter.add(domain)

        should_add = self._should_add(domain_is_known, url_is_known)

        if should_add:
            self.persistent_key_filter.add(domain, url, cursor=self.cursor)
            should_publish = True

            if not domain_is_known:
                self.domain_bloom_filter.add(domain)

            if not url_is_known:
                self.url_bloom_filter.add(url)

        if should_publish:
            priority = self._get_priority(
                domain_is_known,
                url_is_known,
                url_map
            )
            url_map['fetch_priority'] = priority
            await self.publish(url_map)

            return 1

    def _get_priority(self, domain_is_known, url_is_known, url_map):
        """Get crawler priority of url."""
        override = url_map.get("override", None)
        recrawl = url_map.get("recrawl", None)

        # User manually inputted this entity.
        if override:
            return 1
        # Override was set or the domain is unknown.
        elif not domain_is_known:
            return 2
        elif recrawl:
            return 4
        elif domain_is_known and not url_is_known:
            return 3
        else:
            return 5

    def _should_add(self, domain_is_known, url_is_known):
        """Determine of url should be added to the database."""
        return all((
            not (domain_is_known and url_is_known),
            any((
                not domain_is_known and not url_is_known,
                domain_is_known and not url_is_known
            ))
        ))

    def _should_ignore(self, domain_is_known, url_is_known, override, recrawl):
        """Determine if URL should be ignored."""
        return all((
            domain_is_known,
            url_is_known,
            not any((
                override,
                recrawl
            ))
        ))

    def check_entity(self, entity, bloom_filter, key_filter_fn):
        """Check if entity is known."""
        entity_known = entity in bloom_filter

        if entity_known:
            return key_filter_fn(entity, cursor=self.cursor)

        return entity_known

    def exists_domain(self, domain):
        """Domain has been seen."""
        domain_known = domain in self.domain_bloom_filter

        if domain_known:
            return self.persistent_key_filter.exists_domain(
                domain,
                cursor=self.cursor
            )

        return domain_known

    def exists_url(self, domain, url):
        """URL has been seen."""
        url_known = url in self.url_bloom_filter

        if url_known:
            return self.persistent_key_filter.exists_url(
                domain,
                url,
                cursor=self.cursor
            )

        return url_known
