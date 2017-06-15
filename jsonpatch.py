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

""" Apply JSON-Patches (RFC 6902) """

from __future__ import unicode_literals

import collections
import copy
import functools
import inspect
import itertools
import json
import sys

try:
    from collections.abc import MutableMapping, MutableSequence
except ImportError:
    from collections import MutableMapping, MutableSequence

from jsonpointer import JsonPointer, JsonPointerException

# Will be parsed by setup.py to determine package metadata
__author__ = 'Stefan Kögl <stefan@skoegl.net>'
__version__ = '1.16'
__website__ = 'https://github.com/stefankoegl/python-json-patch'
__license__ = 'Modified BSD License'


# pylint: disable=E0611,W0404
if sys.version_info >= (3, 0):
    basestring = (bytes, str)  # pylint: disable=C0103,W0622


class JsonPatchException(Exception):
    """Base Json Patch exception"""


class InvalidJsonPatch(JsonPatchException):
    """ Raised if an invalid JSON Patch is created """


class JsonPatchConflict(JsonPatchException):
    """Raised if patch could not be applied due to conflict situation such as:
    - attempt to add object key then it already exists;
    - attempt to operate with nonexistence object key;
    - attempt to insert value to array at position beyond of it size;
    - etc.
    """


class JsonPatchTestFailed(JsonPatchException, AssertionError):
    """ A Test operation failed """


def multidict(ordered_pairs):
    """Convert duplicate keys values to lists."""
    # read all values into lists
    mdict = collections.defaultdict(list)
    for key, value in ordered_pairs:
        mdict[key].append(value)

    return dict(
        # unpack lists that have only 1 item
        (key, values[0] if len(values) == 1 else values)
        for key, values in mdict.items()
    )


def get_loadjson():
    """ adds the object_pairs_hook parameter to json.load when possible

    The "object_pairs_hook" parameter is used to handle duplicate keys when
    loading a JSON object. This parameter does not exist in Python 2.6. This
    methods returns an unmodified json.load for Python 2.6 and a partial
    function with object_pairs_hook set to multidict for Python versions that
    support the parameter. """

    if sys.version_info >= (3, 3):
        args = inspect.signature(json.load).parameters
    else:
        args = inspect.getargspec(json.load).args
    if 'object_pairs_hook' not in args:
        return json.load

    return functools.partial(json.load, object_pairs_hook=multidict)

json.load = get_loadjson()


def apply_patch(doc, patch, in_place=False):
    """Apply list of patches to specified json document.

    :param doc: Document object.
    :type doc: dict

    :param patch: JSON patch as list of dicts or raw JSON-encoded string.
    :type patch: list or str

    :param in_place: While :const:`True` patch will modify target document.
                     By default patch will be applied to document copy.
    :type in_place: bool

    :return: Patched document object.
    :rtype: dict

    >>> doc = {'foo': 'bar'}
    >>> patch = [{'op': 'add', 'path': '/baz', 'value': 'qux'}]
    >>> other = apply_patch(doc, patch)
    >>> doc is not other
    True
    >>> other == {'foo': 'bar', 'baz': 'qux'}
    True
    >>> patch = [{'op': 'add', 'path': '/baz', 'value': 'qux'}]
    >>> apply_patch(doc, patch, in_place=True) == {'foo': 'bar', 'baz': 'qux'}
    True
    >>> doc == other
    True
    """

    if isinstance(patch, basestring):
        patch = JsonPatch.from_string(patch)
    else:
        patch = JsonPatch(patch)
    return patch.apply(doc, in_place)


def make_patch(src, dst):
    """Generates patch by comparing of two document objects. Actually is
    a proxy to :meth:`JsonPatch.from_diff` method.

    :param src: Data source document object.
    :type src: dict

    :param dst: Data source document object.
    :type dst: dict

    >>> src = {'foo': 'bar', 'numbers': [1, 3, 4, 8]}
    >>> dst = {'baz': 'qux', 'numbers': [1, 4, 7]}
    >>> patch = make_patch(src, dst)
    >>> new = patch.apply(src)
    >>> new == dst
    True
    """

    # TODO: fix patch optimiztion and remove the following check
    # fix when patch with optimization is incorrect
    patch = JsonPatch.from_diff(src, dst)
    new = patch.apply(src)
    if new != dst:
        return JsonPatch.from_diff(src, dst, False)

    return JsonPatch.from_diff(src, dst)


class JsonPatch(object):
    """A JSON Patch is a list of Patch Operations.

    >>> patch = JsonPatch([
    ...     {'op': 'add', 'path': '/foo', 'value': 'bar'},
    ...     {'op': 'add', 'path': '/baz', 'value': [1, 2, 3]},
    ...     {'op': 'remove', 'path': '/baz/1'},
    ...     {'op': 'test', 'path': '/baz', 'value': [1, 3]},
    ...     {'op': 'replace', 'path': '/baz/0', 'value': 42},
    ...     {'op': 'remove', 'path': '/baz/1'},
    ... ])
    >>> doc = {}
    >>> result = patch.apply(doc)
    >>> expected = {'foo': 'bar', 'baz': [42]}
    >>> result == expected
    True

    JsonPatch object is iterable, so you could easily access to each patch
    statement in loop:

    >>> lpatch = list(patch)
    >>> expected = {'op': 'add', 'path': '/foo', 'value': 'bar'}
    >>> lpatch[0] == expected
    True
    >>> lpatch == patch.patch
    True

    Also JsonPatch could be converted directly to :class:`bool` if it contains
    any operation statements:

    >>> bool(patch)
    True
    >>> bool(JsonPatch([]))
    False

    This behavior is very handy with :func:`make_patch` to write more readable
    code:

    >>> old = {'foo': 'bar', 'numbers': [1, 3, 4, 8]}
    >>> new = {'baz': 'qux', 'numbers': [1, 4, 7]}
    >>> patch = make_patch(old, new)
    >>> if patch:
    ...     # document have changed, do something useful
    ...     patch.apply(old)    #doctest: +ELLIPSIS
    {...}
    """
    def __init__(self, patch):
        self.patch = patch

        self.operations = {
            'remove': RemoveOperation,
            'add': AddOperation,
            'replace': ReplaceOperation,
            'move': MoveOperation,
            'test': TestOperation,
            'copy': CopyOperation,
        }

    def __str__(self):
        """str(self) -> self.to_string()"""
        return self.to_string()

    def __bool__(self):
        return bool(self.patch)

    __nonzero__ = __bool__

    def __iter__(self):
        return iter(self.patch)

    def __hash__(self):
        return hash(tuple(self._ops))

    def __eq__(self, other):
        if not isinstance(other, JsonPatch):
            return False
        return self._ops == other._ops

    def __ne__(self, other):
        return not(self == other)

    @classmethod
    def from_string(cls, patch_str):
        """Creates JsonPatch instance from string source.

        :param patch_str: JSON patch as raw string.
        :type patch_str: str

        :return: :class:`JsonPatch` instance.
        """
        patch = json.loads(patch_str)
        return cls(patch)

    @classmethod
    def from_diff(cls, src, dst, optimization=True):
        """Creates JsonPatch instance based on comparing of two document
        objects. Json patch would be created for `src` argument against `dst`
        one.

        :param src: Data source document object.
        :type src: dict

        :param dst: Data source document object.
        :type dst: dict

        :return: :class:`JsonPatch` instance.

        >>> src = {'foo': 'bar', 'numbers': [1, 3, 4, 8]}
        >>> dst = {'baz': 'qux', 'numbers': [1, 4, 7]}
        >>> patch = JsonPatch.from_diff(src, dst)
        >>> new = patch.apply(src)
        >>> new == dst
        True
        """
        def compare_values(path, value, other):
            if value == other:
                return
            if isinstance(value, MutableMapping) and \
                    isinstance(other, MutableMapping):
                for operation in compare_dicts(path, value, other):
                    yield operation
            elif isinstance(value, MutableSequence) and \
                    isinstance(other, MutableSequence):
                for operation in compare_lists(path, value, other):
                    yield operation
            else:
                ptr = JsonPointer.from_parts(path)
                yield {'op': 'replace', 'path': ptr.path, 'value': other}

        def compare_dicts(path, src, dst):
            for key in src:
                if key not in dst:
                    ptr = JsonPointer.from_parts(path + [key])
                    yield {'op': 'remove', 'path': ptr.path}
                    continue
                current = path + [key]
                for operation in compare_values(current, src[key], dst[key]):
                    yield operation
            for key in dst:
                if key not in src:
                    ptr = JsonPointer.from_parts(path + [key])
                    yield {'op': 'add',
                           'path': ptr.path,
                           'value': dst[key]}

        def compare_lists(path, src, dst):
            return _compare_lists(path, src, dst, optimization=optimization)

        return cls(list(compare_values([], src, dst)))

    def to_string(self):
        """Returns patch set as JSON string."""
        return json.dumps(self.patch)

    @property
    def _ops(self):
        return tuple(map(self._get_operation, self.patch))

    def apply(self, obj, in_place=False):
        """Applies the patch to given object.

        :param obj: Document object.
        :type obj: dict

        :param in_place: Tweaks way how patch would be applied - directly to
                         specified `obj` or to his copy.
        :type in_place: bool

        :return: Modified `obj`.
        """

        if not in_place:
            obj = copy.deepcopy(obj)

        for operation in self._ops:
            obj = operation.apply(obj)

        return obj

    def _get_operation(self, operation):
        if 'op' not in operation:
            raise InvalidJsonPatch("Operation does not contain 'op' member")

        op = operation['op']

        if not isinstance(op, basestring):
            raise InvalidJsonPatch("Operation must be a string")

        if op not in self.operations:
            raise InvalidJsonPatch("Unknown operation {0!r}".format(op))

        cls = self.operations[op]
        return cls(operation)


class PatchOperation(object):
    """A single operation inside a JSON Patch."""

    def __init__(self, operation):
        self.location = operation['path']
        self.pointer = JsonPointer(self.location)
        self.operation = operation

    def apply(self, obj):
        """Abstract method that applies patch operation to specified object."""
        raise NotImplementedError('should implement patch operation.')

    def __hash__(self):
        return hash(frozenset(self.operation.items()))

    def __eq__(self, other):
        if not isinstance(other, PatchOperation):
            return False
        return self.operation == other.operation

    def __ne__(self, other):
        return not(self == other)


class RemoveOperation(PatchOperation):
    """Removes an object property or an array element."""

    def apply(self, obj):
        subobj, part = self.pointer.to_last(obj)
        try:
            del subobj[part]
        except (KeyError, IndexError) as ex:
            msg = "can't remove non-existent object '{0}'".format(part)
            raise JsonPatchConflict(msg)

        return obj


class AddOperation(PatchOperation):
    """Adds an object property or an array element."""

    def apply(self, obj):
        try:
            value = self.operation["value"]
        except KeyError as ex:
            raise InvalidJsonPatch(
                "The operation does not contain a 'value' member")

        subobj, part = self.pointer.to_last(obj)

        if isinstance(subobj, MutableSequence):
            if part == '-':
                subobj.append(value)  # pylint: disable=E1103

            elif part > len(subobj) or part < 0:
                raise JsonPatchConflict("can't insert outside of list")

            else:
                subobj.insert(part, value)  # pylint: disable=E1103

        elif isinstance(subobj, MutableMapping):
            if part is None:
                obj = value  # we're replacing the root
            else:
                subobj[part] = value

        else:
            raise TypeError("invalid document type {0}".format(type(subobj)))

        return obj


class ReplaceOperation(PatchOperation):
    """Replaces an object property or an array element by new value."""

    def apply(self, obj):
        try:
            value = self.operation["value"]
        except KeyError as ex:
            raise InvalidJsonPatch(
                "The operation does not contain a 'value' member")

        subobj, part = self.pointer.to_last(obj)

        if part is None:
            return value

        if isinstance(subobj, MutableSequence):
            if part > len(subobj) or part < 0:
                raise JsonPatchConflict("can't replace outside of list")

        elif isinstance(subobj, MutableMapping):
            if not part in subobj:
                msg = "can't replace non-existent object '{0}'".format(part)
                raise JsonPatchConflict(msg)
        else:
            raise TypeError("invalid document type {0}".format(type(subobj)))

        subobj[part] = value
        return obj


class MoveOperation(PatchOperation):
    """Moves an object property or an array element to new location."""

    def apply(self, obj):
        try:
            from_ptr = JsonPointer(self.operation['from'])
        except KeyError as ex:
            raise InvalidJsonPatch(
                "The operation does not contain a 'from' member")

        subobj, part = from_ptr.to_last(obj)
        try:
            value = subobj[part]
        except (KeyError, IndexError) as ex:
            raise JsonPatchConflict(str(ex))

        # If source and target are equal, this is a no-op
        if self.pointer == from_ptr:
            return obj

        if isinstance(subobj, MutableMapping) and \
                self.pointer.contains(from_ptr):
            raise JsonPatchConflict('Cannot move values into its own children')

        obj = RemoveOperation({
            'op': 'remove',
            'path': self.operation['from']
        }).apply(obj)

        obj = AddOperation({
            'op': 'add',
            'path': self.location,
            'value': value
        }).apply(obj)

        return obj


class TestOperation(PatchOperation):
    """Test value by specified location."""

    def apply(self, obj):
        try:
            subobj, part = self.pointer.to_last(obj)
            if part is None:
                val = subobj
            else:
                val = self.pointer.walk(subobj, part)
        except JsonPointerException as ex:
            raise JsonPatchTestFailed(str(ex))

        try:
            value = self.operation['value']
        except KeyError as ex:
            raise InvalidJsonPatch(
                "The operation does not contain a 'value' member")

        if val != value:
            msg = '{0} ({1}) is not equal to tested value {2} ({3})'
            raise JsonPatchTestFailed(msg.format(val, type(val),
                                                 value, type(value)))

        return obj


class CopyOperation(PatchOperation):
    """ Copies an object property or an array element to a new location """

    def apply(self, obj):
        try:
            from_ptr = JsonPointer(self.operation['from'])
        except KeyError as ex:
            raise InvalidJsonPatch(
                "The operation does not contain a 'from' member")

        subobj, part = from_ptr.to_last(obj)
        try:
            value = copy.deepcopy(subobj[part])
        except (KeyError, IndexError) as ex:
            raise JsonPatchConflict(str(ex))

        obj = AddOperation({
            'op': 'add',
            'path': self.location,
            'value': value
        }).apply(obj)

        return obj


def _compare_lists(path, src, dst, optimization=True):
    """Compares two lists objects and return JSON patch about."""
    patch = list(_compare(path, src, dst, *_split_by_common_seq(src, dst)))
    if optimization:
        return list(_optimize(patch))
    return patch


def _longest_common_subseq(src, dst):
    """Returns pair of ranges of longest common subsequence for the `src`
    and `dst` lists.

    >>> src = [1, 2, 3, 4]
    >>> dst = [0, 1, 2, 3, 5]
    >>> # The longest common subsequence for these lists is [1, 2, 3]
    ... # which is located at (0, 3) index range for src list and (1, 4) for
    ... # dst one. Tuple of these ranges we should get back.
    ... assert ((0, 3), (1, 4)) == _longest_common_subseq(src, dst)
    """
    lsrc, ldst = len(src), len(dst)
    drange = list(range(ldst))
    matrix = [[0] * ldst for _ in range(lsrc)]
    z = 0  # length of the longest subsequence
    range_src, range_dst = None, None
    for i, j in itertools.product(range(lsrc), drange):
        if src[i] == dst[j]:
            if i == 0 or j == 0:
                matrix[i][j] = 1
            else:
                matrix[i][j] = matrix[i-1][j-1] + 1
            if matrix[i][j] > z:
                z = matrix[i][j]
            if matrix[i][j] == z:
                range_src = (i-z+1, i+1)
                range_dst = (j-z+1, j+1)
        else:
            matrix[i][j] = 0
    return range_src, range_dst


def _split_by_common_seq(src, dst, bx=(0, -1), by=(0, -1)):
    """Recursively splits the `dst` list onto two parts: left and right.
    The left part contains differences on left from common subsequence,
    same as the right part by for other side.

    To easily understand the process let's take two lists: [0, 1, 2, 3] as
    `src` and [1, 2, 4, 5] for `dst`. If we've tried to generate the binary tree
    where nodes are common subsequence for both lists, leaves on the left
    side are subsequence for `src` list and leaves on the right one for `dst`,
    our tree would looks like::

        [1, 2]
       /     \
    [0]       []
             /  \
          [3]   [4, 5]

    This function generate the similar structure as flat tree, but without
    nodes with common subsequences - since we're don't need them - only with
    left and right leaves::

        []
       / \
    [0]  []
        / \
     [3]  [4, 5]

    The `bx` is the absolute range for currently processed subsequence of
    `src` list.  The `by` means the same, but for the `dst` list.
    """
    # Prevent useless comparisons in future
    bx = bx if bx[0] != bx[1] else None
    by = by if by[0] != by[1] else None

    if not src:
        return [None, by]
    elif not dst:
        return [bx, None]

    # note that these ranges are relative for processed sublists
    x, y = _longest_common_subseq(src, dst)

    if x is None or y is None:  # no more any common subsequence
        return [bx, by]

    return [_split_by_common_seq(src[:x[0]], dst[:y[0]],
                                 (bx[0], bx[0] + x[0]),
                                 (by[0], by[0] + y[0])),
            _split_by_common_seq(src[x[1]:], dst[y[1]:],
                                 (bx[0] + x[1], bx[0] + len(src)),
                                 (by[0] + y[1], by[0] + len(dst)))]


def _compare(path, src, dst, left, right):
    """Same as :func:`_compare_with_shift` but strips emitted `shift` value."""
    for op, _ in _compare_with_shift(path, src, dst, left, right, 0):
        yield op


def _compare_with_shift(path, src, dst, left, right, shift):
    """Recursively compares differences from `left` and `right` sides
    from common subsequences.

    The `shift` parameter is used to store index shift which caused
    by ``add`` and ``remove`` operations.

    Yields JSON patch operations and list index shift.
    """
    if isinstance(left, MutableSequence):
        for item, shift in _compare_with_shift(path, src, dst, *left,
                                               shift=shift):
            yield item, shift
    elif left is not None:
        for item, shift in _compare_left(path, src, left, shift):
            yield item, shift

    if isinstance(right, MutableSequence):
        for item, shift in _compare_with_shift(path, src, dst, *right,
                                               shift=shift):
            yield item, shift
    elif right is not None:
        for item, shift in _compare_right(path, dst, right, shift):
            yield item, shift


def _compare_left(path, src, left, shift):
    """Yields JSON patch ``remove`` operations for elements that are only
    exists in the `src` list."""
    start, end = left
    if end == -1:
        end = len(src)
    # we need to `remove` elements from list tail to not deal with index shift
    for idx in reversed(range(start + shift, end + shift)):
        ptr = JsonPointer.from_parts(path + [str(idx)])
        yield (
            {'op': 'remove',
             # yes, there should be any value field, but we'll use it
             # to apply `move` optimization a bit later and will remove
             # it in _optimize function.
             'value': src[idx - shift],
             'path': ptr.path,
            },
            shift - 1
        )
        shift -= 1


def _compare_right(path, dst, right, shift):
    """Yields JSON patch ``add`` operations for elements that are only
    exists in the `dst` list"""
    start, end = right
    if end == -1:
        end = len(dst)
    for idx in range(start, end):
        ptr = JsonPointer.from_parts(path + [str(idx)])
        yield (
            {'op': 'add', 'path': ptr.path, 'value': dst[idx]},
            shift + 1
        )
        shift += 1


def _optimize(operations):
    """Optimizes operations which was produced by lists comparison.

    Actually it does two kinds of optimizations:

    1. Seeks pair of ``remove`` and ``add`` operations against the same path
       and replaces them with ``replace`` operation.
    2. Seeks pair of ``remove`` and ``add`` operations for the same value
       and replaces them with ``move`` operation.
    """
    result = []
    ops_by_path = {}
    ops_by_value = {}
    add_remove = set(['add', 'remove'])
    for item in operations:
        # could we apply "move" optimization for dict values?
        hashable_value = not isinstance(item['value'],
                                        (MutableMapping, MutableSequence))
        if item['path'] in ops_by_path:
            _optimize_using_replace(ops_by_path[item['path']], item)
            continue
        if hashable_value and item['value'] in ops_by_value:
            prev_item = ops_by_value[item['value']]
            # ensure that we processing pair of add-remove ops
            if set([item['op'], prev_item['op']]) == add_remove:
                _optimize_using_move(prev_item, item)
                ops_by_value.pop(item['value'])
                continue
        result.append(item)
        ops_by_path[item['path']] = item
        if hashable_value:
            ops_by_value[item['value']] = item

    # cleanup
    ops_by_path.clear()
    ops_by_value.clear()
    for item in result:
        if item['op'] == 'remove':
            item.pop('value')  # strip our hack
        yield item


def _optimize_using_replace(prev, cur):
    """Optimises by replacing ``add``/``remove`` with ``replace`` on same path

    For nested strucures, tries to recurse replacement, see #36 """
    prev['op'] = 'replace'
    if cur['op'] == 'add':
        # make recursive patch
        patch = make_patch(prev['value'], cur['value'])
        # check case when dict "remove" is less than "add" and has a same key
        if isinstance(prev['value'], dict) and isinstance(cur['value'], dict) and len(prev['value'].keys()) == 1:
            prev_set = set(prev['value'].keys())
            cur_set = set(cur['value'].keys())
            if prev_set & cur_set == prev_set:
                patch = make_patch(cur['value'], prev['value'])

        if len(patch.patch) == 1 and \
                patch.patch[0]['op'] != 'remove' and \
                patch.patch[0]['path'] and patch.patch[0]['path'].split('/')[1] in prev['value']:
            prev['path'] = prev['path'] + patch.patch[0]['path']
            prev['value'] = patch.patch[0]['value']
        else:
            prev['value'] = cur['value']


def _optimize_using_move(prev_item, item):
    """Optimises JSON patch by using ``move`` operation instead of
    ``remove` and ``add`` against the different paths but for the same value."""
    prev_item['op'] = 'move'
    move_from, move_to = [
        (item['path'], prev_item['path']),
        (prev_item['path'], item['path']),
    ][item['op'] == 'add']
    if item['op'] == 'add':  # first was remove then add
        prev_item['from'] = move_from
        prev_item['path'] = move_to
    else:  # first was add then remove
        head, move_from = move_from.rsplit('/', 1)
        # since add operation was first it incremented
        # overall index shift value. we have to fix this
        move_from = int(move_from) - 1
        prev_item['from'] = head + '/%d' % move_from
        prev_item['path'] = move_to
