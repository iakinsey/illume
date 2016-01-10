"""Test Bloom Filter."""


from illume.error import BloomFilterExceedsErrorRate, BloomFilterSizeOverflow
from illume.error import InsufficientMemory, AllocationValueError
from illume.filter.bloom import BloomFilter, alloc_bitarray
from illume.util import get_available_memory
from pytest import fail, raises


class TestBloomFilter:
    def test_init(self):
        """Assert that the bloom filter computes the appropriate values."""
        max_n = 10000000
        p = .01
        m = 95850583
        k = 6
        current_p = 0.0

        bloom_filter = BloomFilter(max_n, p)

        assert max_n == bloom_filter.max_n
        assert p == bloom_filter.p
        assert m == bloom_filter.m
        assert k == bloom_filter.k
        assert current_p == bloom_filter.current_p

    def test_add_and_check_count(self):
        """Assert n == max_n on max_n inserts."""
        max_n = 10000000
        p = .01
        count = 10000
        bloom_filter = BloomFilter(max_n, p)

        for i in (str(i) for i in range(count)):
            bloom_filter.add(i)

        assert bloom_filter.n == count

    def test_error_rate(self):
        """Assert current_p <= p while n <= max_n."""
        max_n = 10000
        p = .1
        count = 10000
        last_p = 0.0

        bloom_filter = BloomFilter(max_n, p)

        for i in (str(i) for i in range(count)):
            try:
                bloom_filter.add(i)
            except BloomFilterExceedsErrorRate:
                fail("Bloom filter exceeded error rate.")
            else:
                rate_success = last_p < bloom_filter.current_p_float

                assert rate_success, "last_p !< current_p"

                last_p = bloom_filter.current_p_float

    def test_exceed_bounds(self):
        """
        Test bounds checking of bloom filter.

        Insert the maximum number of elements. Then insert one more and assure
        that an exception is raised.
        """
        max_n = 10000
        p = .1

        bloom_filter = BloomFilter(max_n, p)

        for i in (str(i) for i in range(max_n)):
            bloom_filter.add(i)

        # Fail on adding max_n + 1
        with raises(BloomFilterSizeOverflow):
            bloom_filter.add(str(max_n + 1))

        assert bloom_filter.n == max_n, "Value of n equals maximum count."

    def test_fail_allocation(self):
        """
        Test allocation bounds.

        Assert that a bloom filter larger than the current available memory
        doesn't get allocated.
        """
        size = get_available_memory() * 2

        # Allocation should fail due to value being too large.
        with raises(InsufficientMemory):
            alloc_bitarray(size)

        # Allocation should fail due to value being invalid.
        with raises(AllocationValueError):
            alloc_bitarray(-1)

        # TypeError should raise if invalid value was inserted.
        for s in ["", None, [], {}, True, False, set()]:
            with raises(TypeError):
                alloc_bitarray(s)

    def test_fnv1a_values(self):
        """Test accuracy of fnv1a with precomputed values."""

        test_content = "The quick brown fox jumps over the lazy dog."

        # max_n, p, content, values
        values = [
            (10000, .1, test_content, [106, 28839, 9649]),
            (100000, .1, test_content, [182036, 20641, 338500]),
            (1000000, .1, test_content, [2573904, 4330228, 1294025]),
            (10000000, .1, test_content, [40914088, 47462949, 6086521]),
            (100000000, .1, test_content, [424316384, 47462917, 149862370]),
            (10000, .01, "123", [33468, 87452, 70234, 28372, 11158, 89796]),
            (100000, .01, "asd", [817997, 798561, 685518, 666086, 553047, 440010]),
            (1000000, .01, "123asd", [6968780, 5734018, 4499258, 2403188, 1168432, 8657424]),
            (10000000, .01, "asd123(*#^!", [68148260, 32510192, 74413770, 38775706, 3137644, 45041228]),
            (100000000, .001, "初音ミクはかわいいですか", [1109719310, 165476191, 640682858, 1115889527, 153337442, 628544115, 1103750790, 141198711, 616405390])
        ]

        for max_n, p, content, hashes in values:
            count = 0
            bloom_filter = BloomFilter(max_n, p)
            iterable = list(enumerate(bloom_filter._get_hashes(content)))

            for index, hash_ in iterable:
                assert hash_ == hashes[index]
                count += 1

            assert count == len(hashes)
