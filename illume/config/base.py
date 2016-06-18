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
shard_path = lambda s: in_data("{}-{}".format(s, SHARD_ID))


FILTER_HASHER = xxh64
FILTER_HASHER_KEY_SIZE = FILTER_HASHER().digest_size


FRONTIER_KEY_FILTER_DB_PATH = shard_path("frontier")
FRONTIER_URL_BLOOM_MAX_N = 100000000
FRONTIER_URL_BLOOM_P = .01
FRONTIER_DOMAIN_BLOOM_MAX_N = 10000000
FRONTIER_DOMAIN_BLOOM_P = .01


FETCHER_USER_AGENT = "illume"
FETCHER_TIMEOUT_SECONDS = 10
FETCHER_OUTPUT_DIRECTORY = shard_path("fetcher")
FETCHER_MAX_RESPONSE_SIZE = 10485760 # ~10 megabytes
FETCHER_HEADER_MAX_SIZE = 524288 # ~500 kilobytes


PARSER_DROP_FRAGMENTS = True
PARSER_DROP_QUERY = False


TEMP_PREFIX = "illume-"
QUEUE_ENCODING_TYPE = "UTF-8"
