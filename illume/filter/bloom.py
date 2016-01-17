"""Bloom filter.

Implements a bloom filter using the FNV1a 64-bit hash.

TODO make hashes a generator.
"""


from bitarray import bitarray
from decimal import Decimal
from hashes import fnv1a64_composite
from illume.error import BloomFilterSizeOverflow, BloomFilterExceedsErrorRate
from illume.util import check_alloc_size
from math import log, e


def get_optimal_bloom_m(n, p):
    """Compute the optimal bloom filter size."""
    return -((n * log(p)) / pow(log(2), 2))


def get_optimal_bloom_k(m, n, p):
    """Compute the optimal hash function count for a bloom filter."""
    return (m / n) * log(2)


def get_bloom_error_rate(m, k, n):
    """Return the probability that a certain bit is set to 1."""
    return pow(1 - pow(e, -k * (n + .5) / (m - 1)), k)


def alloc_bitarray(m, name=None):
    """Create a bitarray."""
    check_alloc_size(m, name)

    return bitarray(m)


class BloomFilter:

    """
    Implements a bloom filter using the FNV1a 64-bit hash.

    TODO explain each variable in the docstring.
    """

    def __init__(self, max_n, p):
        # Desired maximum value of n.
        self.max_n = max_n
        # Desired error rate
        self.p = p
        # Number of elements in the bloom filter.
        self.n = 0
        # Decimal precision of p
        self.p_digits = Decimal(str(p)).as_tuple().exponent * -1
        # Size of the bloom filter.
        self.m_float = get_optimal_bloom_m(self.max_n, self.p)
        self.m = int(self.m_float)

        # Number of hash functions.
        self.k_float = get_optimal_bloom_k(self.m, self.max_n, self.p)
        self.k = int(self.k_float)

        # Bit array
        self.bit_array = alloc_bitarray(self.m, "BloomFilter.bit_array")

    @property
    def current_p_float(self):
        """Current error rate."""
        return get_bloom_error_rate(self.m_float, self.k_float, self.n)

    @property
    def current_p(self):
        """
        Current error rate with appropriate precision.

        Round the current value of p to the same number of digits as the
        desired value of p in order to account for floating point errors.
        """
        return round(self.current_p_float, self.p_digits)

    def add(self, item):
        """
        Add an item to the bloom filter.

        We probably don't care about success/fail, since that could possibly
        slow it down, but we can always implement it later.
        """
        self.check_bounds()

        for index in self._get_hashes(item):
            self.bit_array[index] = 1

        self.n += 1

    @property
    def error_params(self):
        return {
            "max_n": self.max_n,
            "desired_p": self.p,
            "current_p": self.current_p,
            "current_p_float": self.current_p_float,
            "k": self.k
        }

    def check_bounds(self):
        """Check error rate and size parameters."""
        if self.n == self.max_n:
            raise BloomFilterSizeOverflow(self.error_params)
        elif self.current_p > self.p:
            raise BloomFilterExceedsErrorRate(self.error_params)

    def remove(self, item):
        """
        Remove an item from the bloom filter.

        No.
        """
        raise NotImplementedError()

    def _get_hashes(self, content):
        # TODO make hashes a generator.
        for index in fnv1a64_composite(content, self.k, self.m):
            yield index

    def __len__(self):
        return self.n

    def __contains__(self, item):
        for index in self._get_hashes(item):
            if not self.bit_array[index]:
                return False

        return True
