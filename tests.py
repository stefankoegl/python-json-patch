#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import doctest
import unittest
import jsonpatch
import sys


class ApplyPatchTestCase(unittest.TestCase):

    def test_apply_patch_from_string(self):
        obj = {'foo': 'bar'}
        patch = '[{"op": "add", "path": "/baz", "value": "qux"}]'
        res = jsonpatch.apply_patch(obj, patch)
        self.assertTrue(obj is not res)
        self.assertTrue('baz' in res)
        self.assertEqual(res['baz'], 'qux')

    def test_apply_patch_to_copy(self):
        obj = {'foo': 'bar'}
        res = jsonpatch.apply_patch(obj, [{'op': 'add', 'path': '/baz', 'value': 'qux'}])
        self.assertTrue(obj is not res)

    def test_apply_patch_to_same_instance(self):
        obj = {'foo': 'bar'}
        res = jsonpatch.apply_patch(obj, [{'op': 'add', 'path': '/baz', 'value': 'qux'}],
                                    in_place=True)
        self.assertTrue(obj is res)

    def test_add_object_key(self):
        obj = {'foo': 'bar'}
        res = jsonpatch.apply_patch(obj, [{'op': 'add', 'path': '/baz', 'value': 'qux'}])
        self.assertTrue('baz' in res)
        self.assertEqual(res['baz'], 'qux')

    def test_add_array_item(self):
        obj = {'foo': ['bar', 'baz']}
        res = jsonpatch.apply_patch(obj, [{'op': 'add', 'path': '/foo/1', 'value': 'qux'}])
        self.assertEqual(res['foo'], ['bar', 'qux', 'baz'])

    def test_remove_object_key(self):
        obj = {'foo': 'bar', 'baz': 'qux'}
        res = jsonpatch.apply_patch(obj, [{'op': 'remove', 'path': '/baz'}])
        self.assertTrue('baz' not in res)

    def test_remove_array_item(self):
        obj = {'foo': ['bar', 'qux', 'baz']}
        res = jsonpatch.apply_patch(obj, [{'op': 'remove', 'path': '/foo/1'}])
        self.assertEqual(res['foo'], ['bar', 'baz'])

    def test_replace_object_key(self):
        obj = {'foo': 'bar', 'baz': 'qux'}
        res = jsonpatch.apply_patch(obj, [{'op': 'replace', 'path': '/baz', 'value': 'boo'}])
        self.assertTrue(res['baz'], 'boo')

    def test_replace_whole_document(self):
        obj = {'foo': 'bar'}
        res = jsonpatch.apply_patch(obj, [{'op': 'replace', 'path': '', 'value': {'baz': 'qux'}}])
        self.assertTrue(res['baz'], 'qux')

    def test_replace_array_item(self):
        obj = {'foo': ['bar', 'qux', 'baz']}
        res = jsonpatch.apply_patch(obj, [{'op': 'replace', 'path': '/foo/1',
                                           'value': 'boo'}])
        self.assertEqual(res['foo'], ['bar', 'boo', 'baz'])

    def test_move_object_key(self):
        obj = {'foo': {'bar': 'baz', 'waldo': 'fred'},
               'qux': {'corge': 'grault'}}
        res = jsonpatch.apply_patch(obj, [{'op': 'move', 'from': '/foo/waldo',
                                           'path': '/qux/thud'}])
        self.assertEqual(res, {'qux': {'thud': 'fred', 'corge': 'grault'},
                               'foo': {'bar': 'baz'}})

    def test_move_array_item(self):
        obj =  {'foo': ['all', 'grass', 'cows', 'eat']}
        res = jsonpatch.apply_patch(obj, [{'op': 'move', 'from': '/foo/1', 'path': '/foo/3'}])
        self.assertEqual(res, {'foo': ['all', 'cows', 'eat', 'grass']})

    def test_copy_object_key(self):
        obj = {'foo': {'bar': 'baz', 'waldo': 'fred'},
               'qux': {'corge': 'grault'}}
        res = jsonpatch.apply_patch(obj, [{'op': 'copy', 'from': '/foo/waldo',
                                           'path': '/qux/thud'}])
        self.assertEqual(res, {'qux': {'thud': 'fred', 'corge': 'grault'},
                               'foo': {'bar': 'baz', 'waldo': 'fred'}})

    def test_copy_array_item(self):
        obj =  {'foo': ['all', 'grass', 'cows', 'eat']}
        res = jsonpatch.apply_patch(obj, [{'op': 'copy', 'from': '/foo/1', 'path': '/foo/3'}])
        self.assertEqual(res, {'foo': ['all', 'grass', 'cows', 'grass', 'eat']})


    def test_copy_mutable(self):
        """ test if mutable objects (dicts and lists) are copied by value """
        obj = {'foo': [{'bar': 42}, {'baz': 3.14}], 'boo': []}
        # copy object somewhere
        res = jsonpatch.apply_patch(obj, [{'op': 'copy', 'from': '/foo/0', 'path': '/boo/0' }])
        self.assertEqual(res, {'foo': [{'bar': 42}, {'baz': 3.14}], 'boo': [{'bar': 42}]})
        # modify original object
        res = jsonpatch.apply_patch(res, [{'op': 'add', 'path': '/foo/0/zoo', 'value': 255}])
        # check if that didn't modify the copied object
        self.assertEqual(res['boo'], [{'bar': 42}])


    def test_test_success(self):
        obj =  {'baz': 'qux', 'foo': ['a', 2, 'c']}
        jsonpatch.apply_patch(obj, [{'op': 'test', 'path': '/baz', 'value': 'qux'},
                                    {'op': 'test', 'path': '/foo/1', 'value': 2}])

    def test_test_error(self):
        obj =  {'bar': 'qux'}
        self.assertRaises(jsonpatch.JsonPatchTestFailed,
                          jsonpatch.apply_patch,
                          obj, [{'op': 'test', 'path': '/bar', 'value': 'bar'}])


    def test_test_not_existing(self):
        obj =  {'bar': 'qux'}
        self.assertRaises(jsonpatch.JsonPatchTestFailed,
                          jsonpatch.apply_patch,
                          obj, [{'op': 'test', 'path': '/baz', 'value': 'bar'}])


    def test_test_noval_existing(self):
        obj =  {'bar': 'qux'}
        jsonpatch.apply_patch(obj, [{'op': 'test', 'path': '/bar'}])


    def test_test_noval_not_existing(self):
        obj =  {'bar': 'qux'}
        self.assertRaises(jsonpatch.JsonPatchTestFailed,
                          jsonpatch.apply_patch,
                          obj, [{'op': 'test', 'path': '/baz'}])


    def test_test_noval_not_existing_nested(self):
        obj =  {'bar': {'qux': 2}}
        self.assertRaises(jsonpatch.JsonPatchTestFailed,
                          jsonpatch.apply_patch,
                          obj, [{'op': 'test', 'path': '/baz/qx'}])


    def test_unrecognized_element(self):
        obj = {'foo': 'bar', 'baz': 'qux'}
        res = jsonpatch.apply_patch(obj, [{'op': 'replace', 'path': '/baz', 'value': 'boo', 'foo': 'ignore'}])
        self.assertTrue(res['baz'], 'boo')


    def test_append(self):
        obj = {'foo': [1, 2]}
        res = jsonpatch.apply_patch(obj, [
                {'op': 'add', 'path': '/foo/-', 'value': 3},
                {'op': 'add', 'path': '/foo/-', 'value': 4},
            ])
        self.assertEqual(res['foo'], [1, 2, 3, 4])



class EqualityTestCase(unittest.TestCase):

    def test_patch_equality(self):
        patch1 = jsonpatch.JsonPatch([{ "op": "add", "path": "/a/b/c", "value": "foo" }])
        patch2 = jsonpatch.JsonPatch([{ "path": "/a/b/c", "op": "add", "value": "foo" }])
        self.assertEqual(patch1, patch2)


    def test_patch_unequal(self):
        patch1 = jsonpatch.JsonPatch([{'op': 'test', 'path': '/test'}])
        patch2 = jsonpatch.JsonPatch([{'op': 'test', 'path': '/test1'}])
        self.assertNotEqual(patch1, patch2)

    def test_patch_hash_equality(self):
        patch1 = jsonpatch.JsonPatch([{ "op": "add", "path": "/a/b/c", "value": "foo" }])
        patch2 = jsonpatch.JsonPatch([{ "path": "/a/b/c", "op": "add", "value": "foo" }])
        self.assertEqual(hash(patch1), hash(patch2))


    def test_patch_hash_unequal(self):
        patch1 = jsonpatch.JsonPatch([{'op': 'test', 'path': '/test'}])
        patch2 = jsonpatch.JsonPatch([{'op': 'test', 'path': '/test1'}])
        self.assertNotEqual(hash(patch1), hash(patch2))





class MakePatchTestCase(unittest.TestCase):

    def test_apply_patch_to_copy(self):
        src = {'foo': 'bar', 'boo': 'qux'}
        dst = {'baz': 'qux', 'foo': 'boo'}
        patch = jsonpatch.make_patch(src, dst)
        res = patch.apply(src)
        self.assertTrue(src is not res)

    def test_apply_patch_to_same_instance(self):
        src = {'foo': 'bar', 'boo': 'qux'}
        dst = {'baz': 'qux', 'foo': 'boo'}
        patch = jsonpatch.make_patch(src, dst)
        res = patch.apply(src, in_place=True)
        self.assertTrue(src is res)

    def test_objects(self):
        src = {'foo': 'bar', 'boo': 'qux'}
        dst = {'baz': 'qux', 'foo': 'boo'}
        patch = jsonpatch.make_patch(src, dst)
        res = patch.apply(src)
        self.assertEqual(res, dst)

    def test_arrays(self):
        src = {'numbers': [1, 2, 3], 'other': [1, 3, 4, 5]}
        dst = {'numbers': [1, 3, 4, 5], 'other': [1, 3, 4]}
        patch = jsonpatch.make_patch(src, dst)
        res = patch.apply(src)
        self.assertEqual(res, dst)

    def test_complex_object(self):
        src = {'data': [
            {'foo': 1}, {'bar': [1, 2, 3]}, {'baz': {'1': 1, '2': 2}}
        ]}
        dst = {'data': [
            {'foo': [42]}, {'bar': []}, {'baz': {'boo': 'oom!'}}
        ]}
        patch = jsonpatch.make_patch(src, dst)
        res = patch.apply(src)
        self.assertEqual(res, dst)

    def test_array_add_remove(self):
        # see https://github.com/stefankoegl/python-json-patch/issues/4
        src = {'numbers': [], 'other': [1, 5, 3, 4]}
        dst = {'numbers': [1, 3, 4, 5], 'other': []}
        patch = jsonpatch.make_patch(src, dst)
        res = patch.apply(src)
        self.assertEqual(res, dst)

    def test_add_nested(self):
        # see http://tools.ietf.org/html/draft-ietf-appsawg-json-patch-03#appendix-A.10
        src = {"foo": "bar"}
        patch_obj = [ { "op": "add", "path": "/child", "value": { "grandchild": { } } } ]
        res = jsonpatch.apply_patch(src, patch_obj)
        expected = { "foo": "bar",
                      "child": { "grandchild": { } }
                   }
        self.assertEqual(expected, res)


modules = ['jsonpatch']
coverage_modules = []


def get_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(jsonpatch))
    suite.addTest(unittest.makeSuite(ApplyPatchTestCase))
    suite.addTest(unittest.makeSuite(EqualityTestCase))
    suite.addTest(unittest.makeSuite(MakePatchTestCase))
    return suite


suite = get_suite()

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
