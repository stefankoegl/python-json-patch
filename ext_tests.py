#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# python-json-patch - An implementation of the JSON Patch format
# https://github.com/stefankoegl/python-json-patch
#
# Copyright (c) 2011 Stefan Kögl <stefan@skoegl.net>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. The name of the author may not be used to endorse or promote products
#    derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
# IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
# OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
# THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

""" Script to run external tests, eg from
https://github.com/json-patch/json-patch-tests """

from functools import partial
import doctest
import unittest
import jsonpatch
import sys


class TestCaseTemplate(unittest.TestCase):
    """ A generic test case for running external tests """

    def _test(self, test):
        if not 'doc' in test or not 'patch' in test:
            # incomplete
            return

        if test.get('disabled', False):
            # test is disabled
            return

        if 'error' in test:
            self.assertRaises(
                (jsonpatch.JsonPatchException, jsonpatch.JsonPointerException),
                jsonpatch.apply_patch, test['doc'], test['patch']
                )

        else:
            try:
                res = jsonpatch.apply_patch(test['doc'], test['patch'])
            except jsonpatch.JsonPatchException as jpe:
                raise Exception(test.get('comment', '')) from jpe

            # if there is no 'expected' we only verify that applying the patch
            # does not raies an exception
            if 'expected' in test:
                self.assertEquals(res, test['expected'], test.get('comment', ''))


def make_test_case(tests):

    class MyTestCase(TestCaseTemplate):
        pass

    for n, test in enumerate(tests):
        add_test_method(MyTestCase, 'test_%d' % n, test)

    return MyTestCase


def add_test_method(cls, name, test):
    setattr(cls, name, lambda self: self._test(test))



modules = ['jsonpatch']
coverage_modules = []


def get_suite(filenames):
    suite = unittest.TestSuite()

    for testfile in filenames:
        with open(testfile) as f:
            # we use the (potentially) patched version of json.load here
            tests = jsonpatch.json.load(f)
            cls = make_test_case(tests)
            suite.addTest(unittest.makeSuite(cls))

    return suite


suite = get_suite(sys.argv[1:])

for module in modules:
    m = __import__(module, fromlist=[module])
    coverage_modules.append(m)
    suite.addTest(doctest.DocTestSuite(m))

runner = unittest.TextTestRunner(verbosity=1)

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
    sys.stderr.write("""
No coverage reporting done (Python module "coverage" is missing)
Please install the python-coverage package to get coverage reporting.
""")
    sys.stderr.flush()
