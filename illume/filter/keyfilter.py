"""Key Filter.

Implements a basic composite key filter to determine if it has been seen before.
"""


from illume.filter.bloom import BloomFilter
from illume.filter.persistent_key_filter import PersistentKeyFilter


class KeyFilterResult:
    def __init__(self, keyfilter, domain=None, url=None):
        if domain is None and url is None:
            raise ValueError("Domain and URL cannot both be None.")

    @property
    def domain_in_bloom_filter(self):
        pass

    @property
    def url_in_bloom_filter(self):
        pass

    @property
    def domain_in_database(self):
        pass

    @property
    def url_in_database(self):
        pass


class KeyFilter:
    def __init__(self, path, size=10000000, bloom_error_rate=.01):
        self._size = size
        self._path = path
        self._bloom_error_rate = bloom_error_rate
        self._bloom_filter = BloomFilter(size, bloom_error_rate)
        self._persistent_filter = PersistentKeyFilter(path)

    def add(self, domain, url):
        # Add to bloom filter
        # Add to database
        pass

    def remove(self, domain=None, url=None):
        self._reindex_bloom_filter()

    def seen(self, domain, url):
        # Check domain
        pass

    def in_bloom_filter(self, domain=None, url=None):
        pass

    def in_database(self, domain=None, url=None):
        pass

    def _reindex_bloom_filter(self):
        pass

    @property
    def _persistent_filter(self):
        pass
