from illume import config
from illume.error import QueryError
from illume.filter.persistent_key_filter import PersistentKeyFilter
from os import makedirs
from os.path import join
from uuid import uuid1


hasher = config.get("FILTER_HASHER")
key_size = config.get("FILTER_HASHER_KEY_SIZE")
hash_ = lambda i: hasher(str(i)).digest()
zip_range = lambda i, j: zip(range(i, i + j), range(i + j, i + (j * 2)))
get_pairs = lambda s, k: [(hash_(i), hash_(j)) for i, j in zip_range(s, k)]
reduce_by_index = lambda l, k: [i[k] for i in l]


class TestPersistentKeyFilter:
    def test_init(self):
        # Create database
        filter = self.create_filter()

        # Create tables
        filter._init_db()

        # Check that schema exists
        assert filter._check_if_tables_exist()


    def test_add_and_check(self):
        # Create database
        filter = self.create_filter(key_size)

        # Create hash pairs
        pairs = get_pairs(10, 10)
        false_pairs = get_pairs(30, 10)

        # Add domains and urls
        for domain, url in pairs:
            filter.add(domain, url)

        # Check if domains and urls exist.
        for domain, url in pairs:
            assert filter.exists(domain=domain)
            assert filter.exists(url=url)
            assert filter.exists(domain=domain, url=url)

        # Check that domains and urls that weren't added don't show up.
        for domain, url in false_pairs:
            assert not filter.exists(domain=domain)
            assert not filter.exists(url=url)
            assert not filter.exists(domain=domain, url=url)

        # Assure that no domain or url indicates and error.
        try:
            filter.exists()
        except QueryError:
            pass
        else:
            assert False

    def test_add_and_check_single(self):
        filter = self.create_filter(key_size)
        cursor = filter.create_cursor()

        pairs = get_pairs(10, 10)
        false_pairs = get_pairs(30, 10)

        for domain, url in pairs:
            filter.add(domain, url)

        domains = reduce_by_index(pairs, 0)
        urls = reduce_by_index(pairs, 1)
        false_domains = reduce_by_index(false_pairs, 0)
        false_urls = reduce_by_index(false_pairs, 1)

        for domain in domains:
            assert filter.exists_domain(domain, cursor=cursor)

        for domain, url in pairs:
            assert filter.exists_url(domain, url, cursor=cursor)

        for domain in false_domains:
            assert domain not in domains
            assert not filter.exists_domain(domain, cursor=cursor)

        for domain, url in false_pairs:
            assert url not in urls
            assert not filter.exists_url(domain, url, cursor=cursor)

    def test_add_and_check_bulk(self):
        # Create database
        filter = self.create_filter(key_size)
        # Create hash pairs
        pairs = get_pairs(10, 10)
        domains = set([i[0] for i in pairs])
        urls = set([i[1] for i in pairs])
        false_pairs = get_pairs(30, 10)
        secondary_pairs = get_pairs(40, 10)
        secondary_domains = set(i[0] for i in secondary_pairs)
        secondary_urls = set(i[1] for i in secondary_pairs)
        anomaly = secondary_pairs[int(len(secondary_pairs) / 2)]

        # Add a set of items in bulk
        for success in filter.add_bulk(pairs):
            assert success

        for domain, url in filter.exists_bulk(pairs):
            assert domain in domains
            assert url in urls

            domains.remove(domain)
            urls.remove(url)


        assert len(domains) == 0
        assert len(urls) == 0

        # Assure that items that don't exist in the database don't show up.
        assert len(list(filter.exists_bulk(false_pairs))) == 0

    def test_add_and_check_bulk_with_collision(self):
        # Create database
        filter = self.create_filter(key_size)
        # Create hash pairs
        secondary_pairs = get_pairs(40, 10)
        secondary_domains = set(i[0] for i in secondary_pairs)
        secondary_urls = set(i[1] for i in secondary_pairs)
        anomaly = secondary_pairs[int(len(secondary_pairs) / 2)]

        # Add a set of items in bulk with a duplicate already in the database.
        # Assert that it's insertion failed and another pair can still be
        # added.
        filter.add(*anomaly)
        fail_count = 0

        for success in filter.add_bulk(secondary_pairs):
            if not success:
                fail_count += 1

        assert fail_count == 1

        # Assert that they exist in bulk
        for domain, url in filter.exists_bulk(secondary_pairs):
            assert domain in secondary_domains
            assert url in secondary_urls

            secondary_domains.remove(domain)
            secondary_urls.remove(url)

        assert len(secondary_domains) == 0
        assert len(secondary_urls) == 0

    def create_filter(self, key_size=8):
        # Create/check test folder.
        path = join(config.get("DATA_DIR"), "keyfilter-{}".format(uuid1()))

        # Create database file.
        return PersistentKeyFilter(path, key_size=key_size)
