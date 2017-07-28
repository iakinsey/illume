Illume
======
[![Build Status](https://travis-ci.org/iakinsey/illume.svg?branch=master)](https://travis-ci.org/iakinsey/illume) [![codecov](https://codecov.io/gh/iakinsey/illume/branch/master/graph/badge.svg)](https://codecov.io/gh/iakinsey/illume)

A comprehensive distributed web crawler framework
-------------------------------------------------

Illume is a web crawler application framework written in Python and asyncio. It
is designed to allow a developer to create a web crawler that can run from
anything between a single thread to a distributed cluster with minimal hassle.

Setting up a developer environment
----------------------------------

Run the following set of commands:

```
virtualenv -p `which python3.6` env
source env/bin/activate
python setup.py install
```

Running tests
-------------

1. Complete **Setting up a developer environment**
2. Run the following command:

```
python setup.py test
```

Building documentation
----------------------

1. Complete **Setting up a developer environment**
2. Run the following set of commands:

```
sphinx-apidoc -o docs/ illume/
cd docs
make html
```

Running a produciton crawler
----------------------------

See `tests/test_fetcher_filter_analyzer_integration.py` a basic example.
