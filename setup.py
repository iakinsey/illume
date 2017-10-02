import os
import shlex
import sys

from setuptools.command.test import test
from setuptools import setup, Extension


NAME = 'illume'
VERSION = '0.0.1'


class RunTests(test):
    user_options = [('pytest-args=', 'a', "Arguments to pass to py.test")]

    def initialize_options(self):
        test.initialize_options(self)
        self.pytest_args = []

    def finalize_options(self):
        test.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        from illume import config
        from coverage import Coverage

        config.setenv("test")

        from pytest import main
        from illume.util import remove_or_ignore_dir
        from logging import basicConfig, DEBUG

        basicConfig(level=DEBUG, filename="illume-test.log")

        project_root = config.get("PROJECT_ROOT")
        data_dir = config.get("DATA_DIR")
        cov_config_dir = os.path.join(project_root, '.coveagerc')

        cov = Coverage(config_file=cov_config_dir)
        # Remvoe data directory in case tests failed to complete last time.
        remove_or_ignore_dir(data_dir)
        cov.start()

        exit_code = main(shlex.split(self.pytest_args or ""))

        cov.stop()
        cov.xml_report()

        # Remove data directory if tests passed successfully. Keep it around
        # if tests failed so the developer can troubleshoot the problem.
        if exit_code == 0:
            remove_or_ignore_dir(data_dir)

        sys.exit(exit_code)


extensions = [
    Extension(
        "hashes",
        sources=[
            "Modules/hashes/fnv/hash_32.c",
            "Modules/hashes/fnv/hash_32a.c",
            "Modules/hashes/fnv/hash_64.c",
            "Modules/hashes/fnv/hash_64a.c",
            'Modules/hashes/hashes.c'
        ],
        define_macros=[
            ("PY_MAJOR", sys.version_info.major),
            ("PY_MINOR", sys.version_info.minor)
        ]
    )
]

setup(
    name=NAME,
    version=VERSION,
    author="Ian Kinsey",
    description="Pluggable content crawler",
    license="Proprietary",
    packages=["illume"],
    cmdclass = {
        'test': RunTests
    },
    ext_modules=extensions,
    install_requires=[
        'bitarray==0.8.1',
        'py==1.4.34',
        'pytest==3.1.3',
        'xxhash==1.0.1',
        'psutil==5.2.2',
        'codecov==2.0.9',
    ]
)
