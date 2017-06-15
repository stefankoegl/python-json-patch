#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import json
import doctest
import unittest
import jsonpatch
import jsonpointer
import sys


class ApplyPatchTestCase(unittest.TestCase):

    def test_js_file(self):
        with open('./tests.js', 'r') as f:
            tests = json.load(f)
            for test in tests:
                try:
                    if 'expected' not in test:
                        continue
                    result = jsonpatch.apply_patch(test['doc'], test['patch'])
                    self.assertEqual(result, test['expected'])
                except Exception:
                    if test.get('error'):
                        continue
                    else:
                        raise

    def test_success_if_replaced_dict(self):
        src = [{'a': 1}, {'b': 2}]
        dst = [{'a': 1, 'b': 2}]
        patch = jsonpatch.make_patch(src, dst)
        self.assertEqual(patch.apply(src), dst)

    def test_success_if_raise_no_error(self):
        src = [{}]
        dst = [{'key': ''}]
        patch = jsonpatch.make_patch(src, dst)
        patch.apply(src)
        self.assertTrue(True)

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

    def test_add_replace_whole_document(self):
        obj = {'foo': 'bar'}
        new_obj = {'baz': 'qux'}
        res = jsonpatch.apply_patch(obj, [{'op': 'add', 'path': '', 'value': new_obj}])
        self.assertTrue(res, new_obj)

    def test_replace_array_item(self):
        obj = {'foo': ['bar', 'qux', 'baz']}
        res = jsonpatch.apply_patch(obj, [{'op': 'replace', 'path': '/foo/1',
                                           'value': 'boo'}])
        self.assertEqual(res['foo'], ['bar', 'boo', 'baz'])

    def test_move_object_keyerror(self):
        obj = {'foo': {'bar': 'baz'},
               'qux': {'corge': 'grault'}}
        patch_obj = [ {'op': 'move', 'from': '/foo/non-existent', 'path': '/qux/thud'} ]
        self.assertRaises(jsonpatch.JsonPatchConflict, jsonpatch.apply_patch, obj, patch_obj)

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

    def test_move_array_item_into_other_item(self):
        obj = [{"foo": []}, {"bar": []}]
        patch = [{"op": "move", "from": "/0", "path": "/0/bar/0"}]
        res = jsonpatch.apply_patch(obj, patch)
        self.assertEqual(res, [{'bar': [{"foo": []}]}])

    def test_copy_object_keyerror(self):
        obj = {'foo': {'bar': 'baz'},
               'qux': {'corge': 'grault'}}
        patch_obj = [{'op': 'copy', 'from': '/foo/non-existent', 'path': '/qux/thud'}]
        self.assertRaises(jsonpatch.JsonPatchConflict, jsonpatch.apply_patch, obj, patch_obj)

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

    def test_test_whole_obj(self):
        obj =  {'baz': 1}
        jsonpatch.apply_patch(obj, [{'op': 'test', 'path': '', 'value': obj}])


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
        self.assertRaises(jsonpatch.InvalidJsonPatch,
                          jsonpatch.apply_patch,
                          obj, [{'op': 'test', 'path': '/bar'}])


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


    def test_patch_neq_other_objs(self):
        p = [{'op': 'test', 'path': '/test'}]
        patch = jsonpatch.JsonPatch(p)
        # a patch will always compare not-equal to objects of other types
        self.assertFalse(patch == p)
        self.assertFalse(patch == None)

        # also a patch operation will always compare
        # not-equal to objects of other types
        op = jsonpatch.PatchOperation(p[0])
        self.assertFalse(op == p[0])
        self.assertFalse(op == None)

    def test_str(self):
        patch_obj = [ { "op": "add", "path": "/child", "value": { "grandchild": { } } } ]
        patch = jsonpatch.JsonPatch(patch_obj)

        self.assertEqual(json.dumps(patch_obj), str(patch))
        self.assertEqual(json.dumps(patch_obj), patch.to_string())


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

    def test_should_just_add_new_item_not_rebuild_all_list(self):
        src = {'foo': [1, 2, 3]}
        dst = {'foo': [3, 1, 2, 3]}
        patch = list(jsonpatch.make_patch(src, dst))
        self.assertEqual(len(patch), 1)
        self.assertEqual(patch[0]['op'], 'add')
        res = jsonpatch.apply_patch(src, patch)
        self.assertEqual(res, dst)

    def test_escape(self):
        src = {"x/y": 1}
        dst = {"x/y": 2}
        patch = jsonpatch.make_patch(src, dst)
        self.assertEqual([{"path": "/x~1y", "value": 2, "op": "replace"}], patch.patch)
        res = patch.apply(src)
        self.assertEqual(res, dst)

    def test_root_list(self):
        """ Test making and applying a patch of the root is a list """
        src = [{'foo': 'bar', 'boo': 'qux'}]
        dst = [{'baz': 'qux', 'foo': 'boo'}]
        patch = jsonpatch.make_patch(src, dst)
        res = patch.apply(src)
        self.assertEqual(res, dst)

    def test_make_patch_unicode(self):
        """ Test if unicode keys and values are handled correctly """
        src = {}
        dst = {'\xee': '\xee'}
        patch = jsonpatch.make_patch(src, dst)
        res = patch.apply(src)
        self.assertEqual(res, dst)

    def test_issue40(self):
        """ Tests an issue in _split_by_common_seq reported in #40 """

        src = [8, 7, 2, 1, 0, 9, 4, 3, 5, 6]
        dest = [7, 2, 1, 0, 9, 4, 3, 6, 5, 8]
        patch = jsonpatch.make_patch(src, dest)

    def test_json_patch(self):
        old = {
            'queue': {'teams_out': [{'id': 3, 'reason': 'If tied'}, {'id': 5, 'reason': 'If tied'}]},
        }
        new = {
            'queue': {'teams_out': [{'id': 5, 'reason': 'If lose'}]}
        }
        patch = jsonpatch.make_patch(old, new)
        new_from_patch = jsonpatch.apply_patch(old, patch)
        self.assertEqual(new, new_from_patch)


class OptimizationTests(unittest.TestCase):
    def test_use_replace_instead_of_remove_add(self):
        src = {'foo': [1, 2, 3]}
        dst = {'foo': [3, 2, 3]}
        patch = list(jsonpatch.make_patch(src, dst))
        self.assertEqual(len(patch), 1)
        self.assertEqual(patch[0]['op'], 'replace')
        res = jsonpatch.apply_patch(src, patch)
        self.assertEqual(res, dst)

    def test_use_replace_instead_of_remove_add_nested(self):
        src = {'foo': [{'bar': 1, 'baz': 2}, {'bar': 2, 'baz': 3}]}
        dst = {'foo': [{'bar': 1}, {'bar': 2, 'baz': 3}]}
        patch = list(jsonpatch.make_patch(src, dst))
        self.assertEqual(len(patch), 1)
        self.assertEqual(patch[0]['op'], 'replace')
        res = jsonpatch.apply_patch(src, patch)
        self.assertEqual(res, dst)

    def test_use_move_instead_of_remove_add(self):
        src = {'foo': [4, 1, 2, 3]}
        dst = {'foo': [1, 2, 3, 4]}
        patch = list(jsonpatch.make_patch(src, dst))
        self.assertEqual(len(patch), 1)
        self.assertEqual(patch[0]['op'], 'move')
        res = jsonpatch.apply_patch(src, patch)
        self.assertEqual(res, dst)

    def test_use_move_instead_of_add_remove(self):
        src = {'foo': [1, 2, 3]}
        dst = {'foo': [3, 1, 2]}
        patch = list(jsonpatch.make_patch(src, dst))
        self.assertEqual(len(patch), 1)
        self.assertEqual(patch[0]['op'], 'move')
        res = jsonpatch.apply_patch(src, patch)
        self.assertEqual(res, dst)

    def test_success_if_replace_inside_dict(self):
        src = [{'a': 1, 'foo': {'b': 2, 'd': 5}}]
        dst = [{'a': 1, 'foo': {'b': 3, 'd': 6}}]
        patch = jsonpatch.make_patch(src, dst)
        self.assertEqual(patch.apply(src), dst)

    def test_success_if_replace_single_value(self):
        src = [{'a': 1, 'b': 2, 'd': 5}]
        dst = [{'a': 1, 'c': 3, 'd': 5}]
        patch = jsonpatch.make_patch(src, dst)
        self.assertEqual(patch.apply(src), dst)

    def test_success_if_replaced_by_object(self):
        src = [{'a': 1, 'b': 2, 'd': 5}]
        dst = [{'d': 6}]
        patch = jsonpatch.make_patch(src, dst)
        self.assertEqual(patch.apply(src), dst)

    def test_success_if_correct_patch_appied(self):
        src = [{'a': 1}, {'b': 2}]
        dst = [{'a': 1, 'b': 2}]
        patch = jsonpatch.make_patch(src, dst)
        self.assertEqual(patch.apply(src), dst)

    def test_success_if_correct_expected_patch_appied(self):
        src = [{"a": 1, "b": 2}]
        dst = [{"b": 2, "c": 2}]
        exp = [{'path': '/0', 'value': {'c': 2, 'b': 2}, 'op': 'replace'}]
        patch = jsonpatch.make_patch(src, dst)
        self.assertEqual(patch.patch, exp)

    def test_minimal_patch(self):
        """ Test whether a minimal patch is created, see #36 """
        src = [{"foo": 1, "bar": 2}]
        dst = [{"foo": 2, "bar": 2}]

        patch = jsonpatch.make_patch(src, dst)

        exp = [
            {
                "path": "/0/foo",
                "value": 2,
                "op": "replace"
            }
        ]

        self.assertEqual(patch.patch, exp)


class InvalidInputTests(unittest.TestCase):

    def test_missing_op(self):
        # an "op" member is required
        src = {"foo": "bar"}
        patch_obj = [ { "path": "/child", "value": { "grandchild": { } } } ]
        self.assertRaises(jsonpatch.JsonPatchException, jsonpatch.apply_patch, src, patch_obj)


    def test_invalid_op(self):
        # "invalid" is not a valid operation
        src = {"foo": "bar"}
        patch_obj = [ { "op": "invalid", "path": "/child", "value": { "grandchild": { } } } ]
        self.assertRaises(jsonpatch.JsonPatchException, jsonpatch.apply_patch, src, patch_obj)


class ConflictTests(unittest.TestCase):

    def test_remove_indexerror(self):
        src = {"foo": [1, 2]}
        patch_obj = [ { "op": "remove", "path": "/foo/10"} ]
        self.assertRaises(jsonpatch.JsonPatchConflict, jsonpatch.apply_patch, src, patch_obj)

    def test_remove_keyerror(self):
        src = {"foo": [1, 2]}
        patch_obj = [ { "op": "remove", "path": "/foo/b"} ]
        self.assertRaises(jsonpointer.JsonPointerException, jsonpatch.apply_patch, src, patch_obj)

    def test_remove_keyerror_dict(self):
        src = {'foo': {'bar': 'barz'}}
        patch_obj = [ { "op": "remove", "path": "/foo/non-existent"} ]
        self.assertRaises(jsonpatch.JsonPatchConflict, jsonpatch.apply_patch, src, patch_obj)

    def test_insert_oob(self):
        src = {"foo": [1, 2]}
        patch_obj = [ { "op": "add", "path": "/foo/10", "value": 1} ]
        self.assertRaises(jsonpatch.JsonPatchConflict, jsonpatch.apply_patch, src, patch_obj)

    def test_move_into_child(self):
        src = {"foo": {"bar": {"baz": 1}}}
        patch_obj = [ { "op": "move", "from": "/foo", "path": "/foo/bar" } ]
        self.assertRaises(jsonpatch.JsonPatchException, jsonpatch.apply_patch, src, patch_obj)

    def test_replace_oob(self):
        src = {"foo": [1, 2]}
        patch_obj = [ { "op": "replace", "path": "/foo/10", "value": 10} ]
        self.assertRaises(jsonpatch.JsonPatchConflict, jsonpatch.apply_patch, src, patch_obj)

    def test_replace_missing(self):
        src = {"foo": 1}
        patch_obj = [ { "op": "replace", "path": "/bar", "value": 10} ]
        self.assertRaises(jsonpatch.JsonPatchConflict, jsonpatch.apply_patch, src, patch_obj)


if __name__ == '__main__':
    modules = ['jsonpatch']


    def get_suite():
        suite = unittest.TestSuite()
        suite.addTest(doctest.DocTestSuite(jsonpatch))
        suite.addTest(unittest.makeSuite(ApplyPatchTestCase))
        suite.addTest(unittest.makeSuite(EqualityTestCase))
        suite.addTest(unittest.makeSuite(MakePatchTestCase))
        suite.addTest(unittest.makeSuite(InvalidInputTests))
        suite.addTest(unittest.makeSuite(ConflictTests))
        suite.addTest(unittest.makeSuite(OptimizationTests))
        return suite


    suite = get_suite()

    for module in modules:
        m = __import__(module, fromlist=[module])
        suite.addTest(doctest.DocTestSuite(m))

    runner = unittest.TextTestRunner(verbosity=1)

    result = runner.run(suite)

    if not result.wasSuccessful():
        sys.exit(1)
