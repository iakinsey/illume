from illume.crawler.basic import BasicCrawler
from illume.test.base import IllumeTest
from illume.util import get_temp_file_name


class TestUnixSocket(IllumeTest):
    def test_init(self):
        seed_path = "seed-file"
        crawler = BasicCrawler(seed_path)

        assert crawler.seed_path == seed_path

    def test_start(self):
        return
        seed_path = get_temp_file_name()

        with open(seed_path, 'w') as f:
            f.write("http://google.com\n")
            f.write("http://yahoo.com\n")
            f.write("http://reddit.com\n")

        crawler = BasicCrawler(seed_path)

        crawler.start()
