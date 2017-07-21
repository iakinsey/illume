"""Test configuration."""


from os.path import dirname, abspath, realpath, join
from multiprocessing import cpu_count


NUM_CPUS = cpu_count()
PROJECT_ROOT = abspath(dirname(dirname(dirname(realpath(__file__)))))
DATA_DIR = join(PROJECT_ROOT, "data_test")
TEST_DIR = join(PROJECT_ROOT, "tests")
SHARD_ID = 0
shard_path = lambda s: in_data("{}-{}".format(s, SHARD_ID))
in_data = lambda *a: join(DATA_DIR, *a)


FRONTIER_KEY_FILTER_DB_PATH = "{}-{}".format(in_data("frontier"), SHARD_ID)
TEMP_PREFIX = "illume-test-"

FETCHER_OUTPUT_DIRECTORY = shard_path("fetcher")
FETCHER_PROGRESS_DIR = shard_path("progress")
