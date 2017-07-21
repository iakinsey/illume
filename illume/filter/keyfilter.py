"""Key Filter."""


from illume.filter.bloom import BloomFilter
from illume.filter.persistent_key_filter import PersistentKeyFilter


class KeyFilterResult:

    """Simplified key filter interface."""

    def __init__(self, keyfilter, domain=None, url=None):
        if domain is None and url is None:
            raise ValueError("Domain and URL cannot both be None.")

    @property
    def domain_in_bloom_filter(self):
        """Domain hash exists in bloom filter addresses."""
        pass

    @property
    def url_in_bloom_filter(self):
        """URL hash exists in bloom filter addresses."""
        pass

    @property
    def domain_in_database(self):
        """Domain exists in persistent key filter."""
        pass

    @property
    def url_in_database(self):
        """URL exists in persistent key filter."""
        pass


class KeyFilter:

    """
    Composite key filter.

    Implements a basic composite key filter to determine if element has been
    seen. Queries bloom filter to determine if element has been seen and falls
    back to persistent key filter when bloom filter responds True.

    Args:
        path (str): Database path.
        size (int): Maximum number of elements.
        bloom_error_rate (float): Maximum allowed bloom filter error rate.
    """

    def __init__(self, path, size=10000000, bloom_error_rate=.01):
        self._size = size
        self._path = path
        self._bloom_error_rate = bloom_error_rate
        self._bloom_filter = BloomFilter(size, bloom_error_rate)
        self._persistent_filter = PersistentKeyFilter(path)

    def add(self, domain, url):
        """Add domain and url to database."""
        # Add to bloom filter
        # Add to database
        pass

    def seen(self, domain, url):
        """Check if domain and URL pair have been seen."""
        # Check domain
        pass

    def in_bloom_filter(self, domain=None, url=None):
        """Check if either domain or url have been seen."""
        pass

    def in_database(self, domain=None, url=None):
        """Check if either domain or url exist in database."""
        pass

    def _reindex_bloom_filter(self):
        """Reindex the bloom filter with the persistent key filter."""
        pass

    @property
    def _persistent_filter(self):
        """Persistent key filter."""
        pass
