from functools import partial
from illume import config
from illume.actor import Actor
from illume.error import DatabaseCorrupt
from illume.log import log


class KeyFilter(Actor):
    def on_init(self):
        self.init_bloom_filters()
        self.init_persistent_key_filter()
        self.populate_bloom_filters()

    def init_bloom_filters(self):
        self.url_bloom_filter = BloomFilter(
            config.FRONTIER_URL_BLOOM_MAX_N,
            config.FRONTIER_URL_BLOOM_P
        )

        self.domain_bloom_filter = BloomFilter(
            config.FRONTIER_DOMAIN_BLOOM_MAX_N,
            config.FRONTIER_DOMAIN_BLOOM_P
        )

    def init_persistent_key_filter(self):
        self.key_filter_path = config.FRONTIER_DB_PATH
        self.key_filter_size = config.FILTER_HASHER_KEY_SIZE
        self.key_filter = KeyFilter(key_filter_path, key_filter_size)
        self.cursor = self.key_filter.create_cursor()
        self.exists_url = partial(
            self._check_entity,
            bloom_filter=self.url_bloom_filter,
            key_filter_fn=self.key_filter.exists_url
        )
        self.exists_domain = partial(
            self._check_entity,
            bloom_filter=self.domain_bloom_filter,
            key_filter_fn=self.key_filter.exists_domain
        )

    def populate_bloom_filters(self):
        # Take all data in the database and throw it into the bloom filter.
        pass

    def on_message(self, message):
        url = message['url']
        domain = message['domain']
        override_filter = message.get('override', None)

        domain_is_known = self.exists_domain(domain)
        url_is_known = False
        should_publush = True

        if domain_is_known:
            url_is_known = self.exists_url(url)

        if domain_is_known and url_is_known and not override_filter:
            return

        if not domain_is_known:
            self.domain_bloom_filter.add(domain)

        should_add = self._should_add(domain_is_known, url_is_known)

        if should_add:
            self.key_filter.add(domain, url, cursor=self.cursor)
            should_publish = True

            if not domain_is_known:
                self.domain_bloom_filter.add(domain)

            if not url_is_known:
                self.url_bloom_filter.add(url)
        # Anomalous behaviour, this shouldn't happen.
        elif not domain_is_known and url_is_known:
            # Trigger a warning.
            warning = "Domain {} unknown while url {} is known."
            log.warn(warning.format(domain, url))

            # Correct the error.
            self.key_filter.add(domain, url, cursor=self.cursor)
            self.domain_bloom_filter.add(domain)

            # Publish anyway
            should_publish = True

        if should_publish:
            priority = self._get_priority(domain_is_known, url_is_known, message)
            message['fetch_priority'] = priority
            self.publish(message)

        # TODO If the bloom filter exceeds it's maximum size or error rate, a
        # new one is created and the bloom filter is reindexed. A warning is
        # triggered with the new values.

    def _get_priority(self, domain_is_known, url_is_known, message):
        override = message.get("override", None)
        user_inputted = message.get("user_inputted", None)
        recrawl = message.get("recrawl", None)

        # User manually inputted this entity.
        if user_inputted:
            return 1
        # Override was set or the domain is unknown.
        elif override and not domain_is_known:
            return 2
        elif recrawl:
            return 4
        elif domain_is_known and not url_is_known:
            return 3
        else:
            return 5

    def _should_add(self, domain_is_known, url_is_known):
        return all((
            not (domain_is_known and url_is_known),
            any((
                not domain_is_known and not url_is_known,
                domain_is_known and not url_is_known
            ))
        ))

    def _check_entity(self, entity, bloom_filter, key_filter_fn):
        entity_known = entity in bloom_filter

        if entity_known:
            return key_filter_fn(entity, cursor=self.cursor)

        return entity_known
