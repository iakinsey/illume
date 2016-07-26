from setuptools import setup, Extension
import os
import sys
from setuptools.command.test import test


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

        config.setenv("test")

        from pytest import main
        from illume.util import remove_or_ignore_dir
        from logging import basicConfig, DEBUG

        basicConfig(level=DEBUG, filename="illume-test.log")

        test_dir = config.get("TEST_DIR")
        data_dir = config.get("DATA_DIR")

        # Remvoe data directory in case tests failed to complete last time.
        remove_or_ignore_dir(data_dir)
        exit_code = main(self.pytest_args)

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
    )
]

setup(
    name="illume",
    version="0.0.1",
    author="guy",
    description="Pluggable content crawler",
    license="Proprietary",
    packages=["illume"],
    cmdclass = {'test': RunTests},
    ext_modules=extensions,
    install_requires=[
        'bitarray==0.8.1',
        'psutil==4.1.0',
        'py==1.4.31',
        'pytest==2.9.1',
        'xxhash==0.5.0'
    ]
)
