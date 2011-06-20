#!/usr/bin/env python
# -*- coding: utf-8 -*-

import doctest
import unittest
import sys

modules = ['jsonpatch']
coverage_modules = []

suite = unittest.TestSuite()

for module in modules:
    m = __import__(module, fromlist=[module])
    coverage_modules.append(m)
    suite.addTest(doctest.DocTestSuite(m))

runner = unittest.TextTestRunner(verbosity=2)

try:
    import coverage
except ImportError:
    coverage = None

if coverage is not None:
    coverage.erase()
    coverage.start()

result = runner.run(suite)

if not result.wasSuccessful():
    sys.exit(1)

if coverage is not None:
    coverage.stop()
    coverage.report(coverage_modules)
    coverage.erase()

if coverage is None:
    print >>sys.stderr, """
    No coverage reporting done (Python module "coverage" is missing)
    Please install the python-coverage package to get coverage reporting.
    """
