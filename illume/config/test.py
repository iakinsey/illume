from os.path import dirname, abspath, realpath, join
from multiprocessing import cpu_count


NUM_CPUS = cpu_count()
PROJECT_ROOT = abspath(dirname(dirname(dirname(realpath(__file__)))))
DATA_DIR = join(PROJECT_ROOT, "data_test")
TEST_DIR = join(PROJECT_ROOT, "tests")
in_data = lambda *a: os.path.join(DATA_DIR, *a)
