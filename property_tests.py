#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Property-based tests for jsonpatch, using Hypothesis

These complement the example-based tests in tests.py by checking general
properties (e.g. "applying make_patch(src, dst) to src yields dst") against
many generated documents and patches.

Properties that do not hold yet are marked as expected failures.  Each of them
carries the minimal counterexample Hypothesis found as an explicit @example,
so it fails deterministically, and turns into an "unexpected success" (which
fails the run) once the property holds and the marker can be removed.  Tests
that must pass meanwhile avoid those inputs and say so.

Run more examples with HYPOTHESIS_PROFILE=thorough.
"""

import copy
import json
import os
import unittest

from hypothesis import example, given, note, settings, strategies as st
from hypothesis.stateful import (RuleBasedStateMachine, initialize,
                                 invariant, precondition, rule)

import jsonpatch
from jsonpointer import JsonPointerException


# Nested documents can be slow to generate on CI machines; never fail on timing
settings.register_profile('standard', deadline=None)
settings.register_profile('thorough', deadline=None, max_examples=5000)
settings.load_profile(os.environ.get('HYPOTHESIS_PROFILE', 'standard'))


def json_equal(first, second):
    """ Compare documents the way RFC 6902 compares values in 'test':
    numbers by value, everything else (e.g. true vs 1) by type and value """
    if isinstance(first, bool) or isinstance(second, bool):
        return type(first) is type(second) and first == second
    if isinstance(first, (int, float)) and isinstance(second, (int, float)):
        return first == second
    if isinstance(first, dict) and isinstance(second, dict):
        return set(first) == set(second) and \
            all(json_equal(first[key], second[key]) for key in first)
    if isinstance(first, list) and isinstance(second, list):
        return len(first) == len(second) and \
            all(json_equal(a, b) for a, b in zip(first, second))
    return type(first) is type(second) and first == second


def assert_json_equal(first, second):
    if not json_equal(first, second):
        raise AssertionError('{0!r} != {1!r}'.format(first, second))


def to_pointer(parts):
    """ Build a JSON pointer from object keys and array indices """
    return ''.join('/' + str(part).replace('~', '~0').replace('/', '~1')
                   for part in parts)


def resolve(doc, parts):
    for part in parts:
        doc = doc[part]
    return doc


def locations(doc, parts=()):
    """ Yield the parts of every location in doc, the root included """
    yield parts
    if isinstance(doc, dict):
        children = doc.items()
    elif isinstance(doc, list):
        children = enumerate(doc)
    else:
        return
    for key, value in children:
        yield from locations(value, parts + (key,))


def containers(doc):
    """ Yield every object and array in doc, doc itself included """
    if isinstance(doc, dict):
        yield doc
        for value in doc.values():
            yield from containers(value)
    elif isinstance(doc, list):
        yield doc
        for value in doc:
            yield from containers(value)


def insert(container, key, value):
    """ Insert value into container as the 'add' operation does """
    if isinstance(container, dict):
        container[key] = value
    elif key == '-':
        container.append(value)
    else:
        container.insert(key, value)


def outcome(func, *args, **kwargs):
    """ The result of func, or the type of the exception it raised """
    try:
        return 'result', func(*args, **kwargs)
    except Exception as ex:
        return 'error', type(ex)


def assert_same_outcome(first, second):
    if first[0] == 'result' and second[0] == 'result':
        assert_json_equal(first[1], second[1])
    else:
        assert first == second, '{0!r} != {1!r}'.format(first, second)


json_scalars = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(),
    st.floats(allow_nan=False, allow_infinity=False),
    st.text(max_size=5),
)

# Keys that need escaping in a JSON pointer, or that look like array indices,
# are where pointer handling tends to go wrong
json_keys = st.one_of(
    st.text(max_size=5),
    st.sampled_from(['', '-', '0', '1', '01', '~', '/', '~0', '~1', 'a/b~c']),
)


def json_values(scalars, keys):
    """ Documents built from scalars and object keys """
    return st.recursive(
        scalars,
        lambda children: st.one_of(
            st.lists(children, max_size=5),
            st.dictionaries(keys, children, max_size=5),
        ),
        max_leaves=20,
    )


json_docs = json_values(json_scalars, json_keys)

nonempty_containers = st.one_of(
    st.lists(json_docs, min_size=1, max_size=3),
    st.dictionaries(json_keys, json_docs, min_size=1, max_size=3),
)

# Few distinct values and keys make the two sides of a diff share values,
# which exercises the move detection of the diff algorithm
small_json_docs = json_values(
    st.sampled_from([None, True, False, 0, 1, 'a']),
    st.sampled_from(['a', 'b', '0', '1', '-']),
)


def safe_json_values(scalars, keys):
    """ Documents that avoid the inputs on which make_patch is currently known
    to fail (see test_roundtrip): object keys that are '-' """
    return json_values(scalars, keys.filter(lambda key: key != '-'))


safe_json_docs = safe_json_values(json_scalars, json_keys)
small_safe_json_docs = safe_json_values(
    st.sampled_from([None, True, False, 0, 1, 'a']),
    st.sampled_from(['a', 'b', '0', '1']))


def pairs_of(*doc_strategies):
    """ Two documents, both drawn from the same one of doc_strategies """
    return st.sampled_from(doc_strategies).flatmap(
        lambda docs: st.tuples(docs, docs))


doc_pairs = pairs_of(json_docs, small_json_docs)
safe_doc_pairs = pairs_of(safe_json_docs, small_safe_json_docs)


@st.composite
def pointers(draw, doc):
    """ JSON pointers that may or may not resolve in doc """
    parts = list(draw(st.sampled_from(list(locations(doc)))))
    if draw(st.booleans()):
        parts.append(draw(st.one_of(
            st.sampled_from(['-', '0', '1', '01', '99']), json_keys)))
    return to_pointer(parts)


@st.composite
def operations(draw, doc):
    """ A well-formed operation whose pointers may not resolve in doc """
    op = draw(st.sampled_from(sorted(jsonpatch.JsonPatch.operations)))
    operation = {'op': op, 'path': draw(pointers(doc))}
    if op in ('add', 'replace', 'test'):
        operation['value'] = draw(json_docs)
    if op in ('move', 'copy'):
        operation['from'] = draw(pointers(doc))
    return operation


@st.composite
def docs_with_patches(draw):
    doc = draw(json_docs)
    return doc, draw(st.lists(operations(doc), max_size=5))


patches = docs_with_patches().map(lambda case: case[1])


@st.composite
def existing_locations(draw, doc):
    """ The parts of a location in doc other than the root """
    return list(draw(st.sampled_from(
        [parts for parts in locations(doc) if parts])))


@st.composite
def insert_locations(draw, doc):
    """ The parts of a container in doc and a key or index that 'add' can
    insert at """
    parts = draw(st.sampled_from([
        parts for parts in locations(doc)
        if isinstance(resolve(doc, parts), (dict, list))]))
    container = resolve(doc, parts)
    if isinstance(container, list):
        key = draw(st.one_of(st.integers(0, len(container)), st.just('-')))
    elif container:
        key = draw(st.one_of(json_keys, st.sampled_from(sorted(container))))
    else:
        key = draw(json_keys)
    return list(parts), key


@st.composite
def whole_document_operations(draw):
    """ An operation whose target is the whole document, and its result """
    doc = draw(json_docs)
    sources = [parts for parts in locations(doc) if parts]
    op = draw(st.sampled_from(
        ['add', 'replace', 'move', 'copy'] if sources else ['add', 'replace']))
    if op in ('add', 'replace'):
        value = draw(json_docs)
        return doc, {'op': op, 'path': '', 'value': value}, value
    source = draw(st.sampled_from(sources))
    operation = {'op': op, 'path': '', 'from': to_pointer(source)}
    return doc, operation, resolve(doc, source)


@st.composite
def docs_with_locations(draw):
    """ A document and the parts of a location in it other than the root """
    doc = draw(nonempty_containers)
    return doc, draw(existing_locations(doc))


@st.composite
def moves_into_own_child(draw):
    """ A document and pointers to a location in it and to one of its
    (possibly non-existent) children """
    doc = draw(nonempty_containers)
    source = draw(existing_locations(doc))
    target = source + draw(st.lists(
        st.one_of(st.sampled_from(['-', '0', '1']), json_keys),
        min_size=1, max_size=2))
    return doc, to_pointer(source), to_pointer(target)


class MakePatchProperties(unittest.TestCase):

    def check_roundtrip(self, src, dst):
        patch = jsonpatch.make_patch(src, dst)
        note(patch.patch)
        assert_json_equal(patch.apply(src), dst)

    @given(json_docs)
    def test_diff_of_equal_documents_is_empty(self, doc):
        self.assertEqual(list(jsonpatch.make_patch(doc, copy.deepcopy(doc))),
                         [])

    @unittest.expectedFailure
    @given(doc_pairs)
    # replace of the object member '-' is rejected
    @example(docs=({'-': 0}, {'-': 1}))
    def test_roundtrip(self, docs):
        self.check_roundtrip(*docs)

    @given(safe_doc_pairs)
    # the diff considered e.g. 1 and true equal, #180
    @example(docs=([0], [False]))
    @example(docs=({'a': [1]}, {'b': [True]}))
    def test_roundtrip_of_safe_documents(self, docs):
        self.check_roundtrip(*docs)

    @given(doc_pairs)
    def test_does_not_modify_inputs(self, docs):
        saved = copy.deepcopy(docs)
        # whether make_patch succeeds is checked in test_roundtrip
        outcome(jsonpatch.make_patch, *docs)
        assert_json_equal(list(docs), list(saved))

    @given(safe_doc_pairs)
    @example(docs=({}, {'a': []}))
    def test_result_shares_nothing_with_dst(self, docs):
        src, dst = docs
        result = jsonpatch.make_patch(src, dst).apply(src)
        shared = set(map(id, containers(result))) & set(map(id, containers(dst)))
        self.assertEqual(shared, set())


class ApplyPatchProperties(unittest.TestCase):

    @given(docs_with_patches())
    def test_does_not_modify_document(self, case):
        doc, patch = case
        saved = copy.deepcopy(doc)
        # also when applying fails
        outcome(jsonpatch.apply_patch, doc, patch)
        assert_json_equal(doc, saved)

    @given(docs_with_patches())
    @example(case=({}, [{'op': 'add', 'path': '/a', 'value': []},
                        {'op': 'add', 'path': '/a/-', 'value': 1}]))
    def test_does_not_modify_patch(self, case):
        doc, patch = case
        saved = copy.deepcopy(patch)
        outcome(jsonpatch.apply_patch, doc, patch)
        assert_json_equal(patch, saved)

    @unittest.expectedFailure
    @given(docs_with_patches())
    # 'move' from the whole document crashes for array roots
    @example(case=([], [{'op': 'move', 'from': '', 'path': '/-'}]))
    # 'copy' or 'move' from the '-' of an array crashes
    @example(case=([0], [{'op': 'copy', 'from': '/-', 'path': '/0'}]))
    # operations on the whole document crash if it is a scalar
    @example(case=(None, [{'op': 'remove', 'path': ''}]))
    def test_raises_only_documented_exceptions(self, case):
        doc, patch = case
        try:
            jsonpatch.apply_patch(doc, patch)
        except (jsonpatch.JsonPatchException, JsonPointerException):
            pass

    @unittest.expectedFailure
    @given(st.lists(st.one_of(
        json_docs,
        st.dictionaries(st.sampled_from(['op', 'path', 'from', 'value']),
                        json_docs),
        st.fixed_dictionaries(
            {'op': st.sampled_from(sorted(jsonpatch.JsonPatch.operations))},
            optional={'path': json_docs, 'from': json_docs,
                      'value': json_docs}),
    )))
    # patch elements that are not objects
    @example(patch=[0])
    # 'from' that is not a string
    @example(patch=[{'op': 'copy', 'from': 0, 'path': '/a'}])
    def test_malformed_patch_raises_documented_exceptions(self, patch):
        try:
            jsonpatch.apply_patch({}, patch)
        except (jsonpatch.JsonPatchException, JsonPointerException):
            pass

    @given(docs_with_patches())
    def test_in_place_gives_same_result(self, case):
        doc, patch = case
        assert_same_outcome(
            outcome(jsonpatch.apply_patch, doc, copy.deepcopy(patch)),
            outcome(jsonpatch.apply_patch, copy.deepcopy(doc),
                    copy.deepcopy(patch), in_place=True))

    @given(docs_with_patches())
    def test_patch_as_string_gives_same_result(self, case):
        doc, patch = case
        assert_same_outcome(
            outcome(jsonpatch.apply_patch, doc, copy.deepcopy(patch)),
            outcome(jsonpatch.apply_patch, doc, json.dumps(patch)))


class OperationProperties(unittest.TestCase):

    @unittest.expectedFailure
    @given(whole_document_operations())
    # 'add' crashes if the document is a scalar, unlike 'replace'
    @example(case=(None, {'op': 'add', 'path': '', 'value': 0}, 0))
    def test_whole_document_as_target(self, case):
        doc, operation, expected = case
        assert_json_equal(jsonpatch.apply_patch(doc, [operation]), expected)

    @given(st.one_of(st.lists(json_docs, max_size=3),
                     st.dictionaries(json_keys, json_docs, max_size=3)))
    @example(doc={})
    def test_copy_whole_document(self, doc):
        target = '/-' if isinstance(doc, list) else '/copy'
        expected = copy.deepcopy(doc)
        insert(expected, target[1:], copy.deepcopy(doc))
        result = jsonpatch.apply_patch(
            doc, [{'op': 'copy', 'from': '', 'path': target}])
        assert_json_equal(result, expected)

    # RFC 6902, 4.4: a location cannot be moved into one of its children;
    # only enforced if the location is an object member
    @unittest.expectedFailure
    @given(moves_into_own_child())
    @example(case=([[], []], '/0', '/0/0'))
    def test_move_into_own_child_fails(self, case):
        doc, source, target = case
        with self.assertRaises((jsonpatch.JsonPatchException,
                                JsonPointerException)):
            jsonpatch.apply_patch(
                doc, [{'op': 'move', 'from': source, 'path': target}])

    # '-' is rejected even where it is an object key, not an array index
    @unittest.expectedFailure
    @given(docs_with_locations(), json_docs)
    @example(case=({'-': None}, ['-']), value=0)
    def test_replace_any_existing_location(self, case, value):
        doc, parts = case
        result = jsonpatch.apply_patch(
            doc, [{'op': 'replace', 'path': to_pointer(parts), 'value': value}])
        assert_json_equal(resolve(result, parts), value)

    # RFC 6902, 4.6: literals like true are only equal to themselves, although
    # Python considers 1 and True equal, #216
    @given(doc_pairs)
    @example(values=(1, True))
    @example(values=([1], [True]))
    @example(values=({'a': 0}, {'a': False}))
    @example(values=(1, 1.0))
    def test_test_operation_uses_json_equality(self, values):
        value, tested = values
        result = outcome(jsonpatch.apply_patch, {'a': value},
                         [{'op': 'test', 'path': '/a', 'value': tested}])
        if json_equal(value, tested):
            self.assertEqual(result[0], 'result')
        else:
            self.assertEqual(result, ('error', jsonpatch.JsonPatchTestFailed))


class JsonPatchProperties(unittest.TestCase):

    @given(patches)
    def test_string_roundtrip(self, operations):
        patch = jsonpatch.JsonPatch(operations)
        self.assertEqual(jsonpatch.JsonPatch.from_string(patch.to_string()),
                         patch)

    # hashing fails for operations whose value is an array or object
    @unittest.expectedFailure
    @given(patches)
    @example(operations=[{'op': 'add', 'path': '/a', 'value': []}])
    def test_equal_patches_have_equal_hashes(self, operations):
        patch = jsonpatch.JsonPatch(operations)
        other = jsonpatch.JsonPatch(copy.deepcopy(operations))
        self.assertEqual(patch, other)
        self.assertEqual(hash(patch), hash(other))


class PatchOperationMachine(RuleBasedStateMachine):
    """ Applies valid operations one at a time to a document and compares
    each result with a direct implementation of RFC 6902.

    Inputs covered by separate tests in OperationProperties are left
    out: the whole document as target or source of an operation, moving a
    location into its own children, replacing an object member '-', and
    testing values which are equal in Python but not in JSON. """

    def __init__(self):
        super(PatchOperationMachine, self).__init__()
        self.initial = {}
        self.doc = {}
        self.patch = []

    @initialize(doc=st.dictionaries(json_keys, json_docs, max_size=5))
    def start(self, doc):
        self.initial = copy.deepcopy(doc)
        self.doc = doc

    def apply(self, operation, expected):
        before = copy.deepcopy(self.doc)
        result = jsonpatch.apply_patch(self.doc, [operation])
        assert_json_equal(result, expected)
        assert_json_equal(self.doc, before)
        self.doc = result
        self.patch.append(copy.deepcopy(operation))

    @rule(data=st.data(), value=json_docs)
    def add(self, data, value):
        parts, key = data.draw(insert_locations(self.doc))
        expected = copy.deepcopy(self.doc)
        insert(resolve(expected, parts), key, copy.deepcopy(value))
        self.apply({'op': 'add', 'path': to_pointer(parts + [key]),
                    'value': value}, expected)

    @precondition(lambda self: self.doc)
    @rule(data=st.data())
    def remove(self, data):
        parts = data.draw(existing_locations(self.doc))
        expected = copy.deepcopy(self.doc)
        del resolve(expected, parts[:-1])[parts[-1]]
        self.apply({'op': 'remove', 'path': to_pointer(parts)}, expected)

    @precondition(lambda self: self.doc)
    @rule(data=st.data(), value=json_docs)
    def replace(self, data, value):
        candidates = [parts for parts in locations(self.doc) if parts and not (
            isinstance(resolve(self.doc, parts[:-1]), dict) and parts[-1] == '-')]
        if not candidates:
            return
        parts = list(data.draw(st.sampled_from(candidates)))
        expected = copy.deepcopy(self.doc)
        resolve(expected, parts[:-1])[parts[-1]] = copy.deepcopy(value)
        self.apply({'op': 'replace', 'path': to_pointer(parts),
                    'value': value}, expected)

    @precondition(lambda self: self.doc)
    @rule(data=st.data())
    def move(self, data):
        source = data.draw(existing_locations(self.doc))
        expected = copy.deepcopy(self.doc)
        value = resolve(expected, source[:-1]).pop(source[-1])
        # the target location is evaluated after removing the source
        parts, key = data.draw(insert_locations(expected))
        source, target = to_pointer(source), to_pointer(parts + [key])
        if target.startswith(source + '/'):
            return
        insert(resolve(expected, parts), key, value)
        self.apply({'op': 'move', 'from': source, 'path': target}, expected)

    @precondition(lambda self: self.doc)
    @rule(data=st.data())
    def copy(self, data):
        source = data.draw(existing_locations(self.doc))
        parts, key = data.draw(insert_locations(self.doc))
        expected = copy.deepcopy(self.doc)
        insert(resolve(expected, parts), key,
               copy.deepcopy(resolve(self.doc, source)))
        self.apply({'op': 'copy', 'from': to_pointer(source),
                    'path': to_pointer(parts + [key])}, expected)

    @rule(data=st.data())
    def test_equal(self, data):
        parts = data.draw(st.sampled_from(list(locations(self.doc))))
        value = copy.deepcopy(resolve(self.doc, parts))
        self.apply({'op': 'test', 'path': to_pointer(parts), 'value': value},
                   copy.deepcopy(self.doc))

    @rule(data=st.data(), value=json_docs)
    def test_different(self, data, value):
        parts = data.draw(st.sampled_from(list(locations(self.doc))))
        if value == resolve(self.doc, parts):
            return
        operation = {'op': 'test', 'path': to_pointer(parts), 'value': value}
        result = outcome(jsonpatch.apply_patch, self.doc, [operation])
        assert result == ('error', jsonpatch.JsonPatchTestFailed), result

    @invariant()
    def patch_gives_same_result(self):
        assert_json_equal(jsonpatch.apply_patch(self.initial, self.patch),
                          self.doc)


PatchOperationTests = PatchOperationMachine.TestCase


if __name__ == '__main__':
    unittest.main()
