#!/usr/bin/env python
# -*- coding: utf-8 -*-

import doctest
import unittest
import jsonpatch


class ValidatePatchTestCase(unittest.TestCase):

    def test_json_not_list(self):
        patch = '{"add": "/baz", "value": "qux"}'
        self.assertRaises(jsonpatch.JsonPatchInvalid,
                jsonpatch.JsonPatch, patch)

    def test_patch_invalid_type(self):
        patch = object()
        self.assertRaises(jsonpatch.JsonPatchInvalid,
                jsonpatch.JsonPatch, patch)

    def test_patch_invalid_json(self):
        patch = 'XXX'
        self.assertRaises(jsonpatch.JsonPatchInvalid,
                jsonpatch.JsonPatch, patch)

    def test_patch_buried_invalid_operation(self):
        patch = [
            {"remove": "/ping"},
            {"destroy": "/ping"},  # Invalid!
        ]
        self.assertRaises(jsonpatch.JsonPatchInvalid,
                jsonpatch.JsonPatch, patch)

    def test_patch_invalid_operation_name_conflict(self):
        patch = [
            {"add": "/ping", "value": "pong", "remove": "/pink"},
        ]
        self.assertRaises(jsonpatch.JsonPatchInvalid,
                jsonpatch.JsonPatch, patch)

    def test_unknown_operation(self):
        operation = [{"destroy": "/baz"}]
        self.assertRaises(jsonpatch.JsonPatchInvalid,
                jsonpatch.JsonPatch, operation)

    def test_valid_add_operation(self):
        operation = {"add": "/ping", "value": "pong"}
        jsonpatch.AddOperation(operation)

    def test_invalid_add_operation_no_value(self):
        operation = {"add": "/ping"}
        self.assertRaises(jsonpatch.JsonPatchInvalid,
                jsonpatch.AddOperation, operation)

    def test_invalid_add_operation_bad_pointer(self):
        operation = {"add": "ping", "value": "pong"}
        self.assertRaises(jsonpatch.JsonPointerInvalid,
                jsonpatch.AddOperation, operation)

    def test_valid_remove_operation(self):
        operation = {"remove": "/ping"}
        jsonpatch.RemoveOperation(operation)

    def test_invalid_remove_operation_extra_key(self):
        operation = {"remove": "/ping", "value": "pong"}
        self.assertRaises(jsonpatch.JsonPatchInvalid,
                jsonpatch.RemoveOperation, operation)

    def test_invalid_remove_operation_bad_pointer(self):
        operation = {"remove": "ping"}
        self.assertRaises(jsonpatch.JsonPointerInvalid,
                jsonpatch.RemoveOperation, operation)

    def test_valid_replace_operation(self):
        operation = {"replace": "/ping", "value": "pong"}
        jsonpatch.ReplaceOperation(operation)

    def test_invalid_replace_operation_no_value(self):
        operation = {"replace": "/ping"}
        self.assertRaises(jsonpatch.JsonPatchInvalid,
                jsonpatch.ReplaceOperation, operation)

    def test_invalid_replace_operation_bad_pointer(self):
        operation = {"replace": "ping", "value": "pong"}
        self.assertRaises(jsonpatch.JsonPointerInvalid,
                jsonpatch.ReplaceOperation, operation)

    def test_valid_move_operation(self):
        operation = {"move": "/ping", "to": "/pong"}
        jsonpatch.MoveOperation(operation)

    def test_invalid_move_operation_no_to(self):
        operation = {"move": "/ping"}
        self.assertRaises(jsonpatch.JsonPatchInvalid,
                jsonpatch.MoveOperation, operation)

    def test_invalid_move_operation_bad_pointer(self):
        operation = {"move": "ping", "to": "/pong"}
        self.assertRaises(jsonpatch.JsonPointerInvalid,
                jsonpatch.MoveOperation, operation)

    def test_invalid_move_operation_bad_to_pointer(self):
        operation = {"move": "/ping", "to": "pong"}
        self.assertRaises(jsonpatch.JsonPointerInvalid,
                jsonpatch.MoveOperation, operation)

    def test_valid_test_operation(self):
        operation = {"test": "/ping", "value": "pong"}
        jsonpatch.TestOperation(operation)

    def test_invalid_test_operation_no_value(self):
        operation = {"test": "/ping"}
        self.assertRaises(jsonpatch.JsonPatchInvalid,
                jsonpatch.TestOperation, operation)

    def test_invalid_test_operation_bad_pointer(self):
        operation = {"test": "ping", "value": "pong"}
        self.assertRaises(jsonpatch.JsonPointerInvalid,
                jsonpatch.TestOperation, operation)


class ApplyPatchTestCase(unittest.TestCase):

    def test_apply_patch_from_string(self):
        obj = {'foo': 'bar'}
        patch = '[{"add": "/baz", "value": "qux"}]'
        res = jsonpatch.apply_patch(obj, patch)
        self.assertTrue(obj is not res)
        self.assertTrue('baz' in res)
        self.assertEqual(res['baz'], 'qux')

    def test_apply_patch_to_copy(self):
        obj = {'foo': 'bar'}
        res = jsonpatch.apply_patch(obj, [{'add': '/baz', 'value': 'qux'}])
        self.assertTrue(obj is not res)

    def test_apply_patch_to_same_instance(self):
        obj = {'foo': 'bar'}
        res = jsonpatch.apply_patch(obj, [{'add': '/baz', 'value': 'qux'}],
                                    in_place=True)
        self.assertTrue(obj is res)

    def test_add_object_key(self):
        obj = {'foo': 'bar'}
        res = jsonpatch.apply_patch(obj, [{'add': '/baz', 'value': 'qux'}])
        self.assertTrue('baz' in res)
        self.assertEqual(res['baz'], 'qux')

    def test_add_array_item(self):
        obj = {'foo': ['bar', 'baz']}
        res = jsonpatch.apply_patch(obj, [{'add': '/foo/1', 'value': 'qux'}])
        self.assertEqual(res['foo'], ['bar', 'qux', 'baz'])

    def test_remove_object_key(self):
        obj = {'foo': 'bar', 'baz': 'qux'}
        res = jsonpatch.apply_patch(obj, [{'remove': '/baz'}])
        self.assertTrue('baz' not in res)

    def test_remove_array_item(self):
        obj = {'foo': ['bar', 'qux', 'baz']}
        res = jsonpatch.apply_patch(obj, [{'remove': '/foo/1'}])
        self.assertEqual(res['foo'], ['bar', 'baz'])

    def test_replace_object_key(self):
        obj = {'foo': 'bar', 'baz': 'qux'}
        res = jsonpatch.apply_patch(obj, [{'replace': '/baz', 'value': 'boo'}])
        self.assertTrue(res['baz'], 'boo')

    def test_replace_array_item(self):
        obj = {'foo': ['bar', 'qux', 'baz']}
        res = jsonpatch.apply_patch(obj, [{'replace': '/foo/1',
                                           'value': 'boo'}])
        self.assertEqual(res['foo'], ['bar', 'boo', 'baz'])

    def test_move_object_key(self):
        obj = {'foo': {'bar': 'baz', 'waldo': 'fred'},
               'qux': {'corge': 'grault'}}
        res = jsonpatch.apply_patch(obj, [{'move': '/foo/waldo',
                                           'to': '/qux/thud'}])
        self.assertEqual(res, {'qux': {'thud': 'fred', 'corge': 'grault'},
                               'foo': {'bar': 'baz'}})

    def test_move_array_item(self):
        obj =  {'foo': ['all', 'grass', 'cows', 'eat']}
        res = jsonpatch.apply_patch(obj, [{'move': '/foo/1', 'to': '/foo/2'}])
        self.assertEqual(res, {'foo': ['all', 'cows', 'grass', 'eat']})

    def test_test_success(self):
        obj =  {'baz': 'qux', 'foo': ['a', 2, 'c']}
        jsonpatch.apply_patch(obj, [{'test': '/baz', 'value': 'qux'},
                                    {'test': '/foo/1', 'value': 2}])

    def test_test_error(self):
        obj =  {'bar': 'qux'}
        self.assertRaises(AssertionError,
                          jsonpatch.apply_patch,
                          obj, [{'test': '/bar', 'value': 'bar'}])

    def test_apply_invalid_patch(self):
        obj = {'foo': 'bar'}
        patch = {'destroy': '/foo'}
        self.assertRaises(jsonpatch.JsonPatchInvalid,
                jsonpatch.apply_patch, obj, patch)


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
        patch_obj = [ { "add": "/child", "value": { "grandchild": { } } } ]
        res = jsonpatch.apply_patch(src, patch_obj)
        expected = { "foo": "bar",
                      "child": { "grandchild": { } }
                   }
        self.assertEqual(expected, res)


class JsonPointerTestCase(unittest.TestCase):

    def test_ascii(self):
        ptr = jsonpatch.JsonPointer('/asdf')
        obj = {u'asdf': 12}
        self.assertEqual(12, ptr.find_value(obj))

    def test_unicode(self):
        ptr = jsonpatch.JsonPointer(u'/\u2022a')
        obj = {u'\u2022a': 12}
        self.assertEqual(12, ptr.find_value(obj))

    def test_empty_path(self):
        ptr = jsonpatch.JsonPointer(u'')
        obj = {u'asdf': 12}
        self.assertEqual({u'asdf': 12}, ptr.find_value(obj))

    def test_empty_token(self):
        ptr = jsonpatch.JsonPointer(u'/')
        obj = {u'': 12}
        self.assertEqual(12, ptr.find_value(obj))

    def test_array_index(self):
        ptr = jsonpatch.JsonPointer('/1')
        obj = [5, 6, 7]
        self.assertEqual(6, ptr.find_value(obj))

    def test_nested(self):
        ptr = jsonpatch.JsonPointer('/a/s/d/f')
        obj = {u'a': {u's': {u'd': {u'f': 12}}}}
        self.assertEqual(12, ptr.find_value(obj))

    def test_nested_empty_token(self):
        ptr = jsonpatch.JsonPointer('/a/s/d//f')
        obj = {u'a': {u's': {u'd': {'': {u'f': 12}}}}}
        self.assertEqual(12, ptr.find_value(obj))

    def test_nested_array_index(self):
        ptr = jsonpatch.JsonPointer('/a/1')
        obj = {u'a': [5, 6, 7]}
        self.assertEqual(6, ptr.find_value(obj))

    def test_tilde(self):
        ptr = jsonpatch.JsonPointer(u'/~0a')
        obj = {u'~a': 12}
        self.assertEqual(12, ptr.find_value(obj))

    def test_forward_slash(self):
        ptr = jsonpatch.JsonPointer(u'/~1a')
        obj = {u'/a': 12}
        self.assertEqual(12, ptr.find_value(obj))

    def test_rfc_examples(self):
        obj = {
            "foo": ["bar", "baz"],
            "": 0,
            "a/b": 1,
            "c%d": 2,
            "e^f": 3,
            "g|h": 4,
            "i\\j": 5,
            "k\"l": 6,
            " ": 7,
            "m~n": 8,
        }

        self.assertEqual(obj, jsonpatch.JsonPointer("").find_value(obj))
        self.assertEqual(["bar", "baz"],
                jsonpatch.JsonPointer("/foo").find_value(obj))
        self.assertEqual("bar", jsonpatch.JsonPointer("/foo/0").find_value(obj))
        self.assertEqual(0, jsonpatch.JsonPointer("/").find_value(obj))
        self.assertEqual(1, jsonpatch.JsonPointer("/a~1b").find_value(obj))
        self.assertEqual(2, jsonpatch.JsonPointer("/c%d").find_value(obj))
        self.assertEqual(3, jsonpatch.JsonPointer("/e^f").find_value(obj))
        self.assertEqual(4, jsonpatch.JsonPointer("/g|h").find_value(obj))
        self.assertEqual(5, jsonpatch.JsonPointer("/i\\j").find_value(obj))
        self.assertEqual(6, jsonpatch.JsonPointer("/k\"l").find_value(obj))
        self.assertEqual(7, jsonpatch.JsonPointer("/ ").find_value(obj))
        self.assertEqual(8, jsonpatch.JsonPointer("/m~0n").find_value(obj))

    def test_unresolvable(self):
        ptr = jsonpatch.JsonPointer('/a/b')
        obj = {u'a': 12}
        self.assertRaises(TypeError, ptr.find_value, obj)

    def test_array_index_unresolvable(self):
        ptr = jsonpatch.JsonPointer('/3')
        obj = [5, 6, 7]
        self.assertRaises(IndexError, ptr.find_value, obj)

    def test_array_index_not_array(self):
        ptr = jsonpatch.JsonPointer('/3')
        obj = {u'a': 123}
        self.assertRaises(KeyError, ptr.find_value, obj)

    def test_bad_pointer(self):
        self.assertRaises(jsonpatch.JsonPointerInvalid,
                jsonpatch.JsonPointer, 'a')


def suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(jsonpatch))
    suite.addTest(unittest.makeSuite(ValidatePatchTestCase))
    suite.addTest(unittest.makeSuite(ApplyPatchTestCase))
    suite.addTest(unittest.makeSuite(MakePatchTestCase))
    suite.addTest(unittest.makeSuite(JsonPointerTestCase))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
