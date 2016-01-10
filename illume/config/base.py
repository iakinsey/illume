from multiprocessing import cpu_count
from os import environ
from os.path import dirname, abspath, realpath, join
from xxhash import xxh64


NUM_CPUS = cpu_count()
PROJECT_ROOT = abspath(dirname(dirname(dirname(realpath(__file__)))))
DATA_DIR = environ.get("ILLUME_DATA_DIR", join(PROJECT_ROOT, "data"))
in_data = lambda *a: os.path.join(DATA_DIR, *a)


FILTER_HASHER = xxh64
FILTER_HASHER_KEY_SIZE = FILTER_HASHER().digest_size
