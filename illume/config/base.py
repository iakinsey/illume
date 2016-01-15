from multiprocessing import cpu_count
from os import environ
from os.path import dirname, abspath, realpath, join
from xxhash import xxh64


NUM_CPUS = cpu_count()
SHARD_ID = environ.get("ILLUME_SHARD_ID", 0)
PROJECT_ROOT = abspath(dirname(dirname(dirname(realpath(__file__)))))
DATA_DIR = environ.get("ILLUME_DATA_DIR", join(PROJECT_ROOT, "data"))
LOG_NAME = "illume"
in_data = lambda *a: join(DATA_DIR, *a)


FILTER_HASHER = xxh64
FILTER_HASHER_KEY_SIZE = FILTER_HASHER().digest_size


FRONTIER_KEY_FILTER_DB_PATH = in_data("frontier")
FRONTIER_URL_BLOOM_MAX_N = 100000000
FRONTIER_URL_BLOOM_P = .01
FRONTIER_DOMAIN_BLOOM_MAX_N = 10000000
FRONTIER_DOMAIN_BLOOM_P = .01
