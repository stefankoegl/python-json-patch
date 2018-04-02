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
import json
import sys

from jsonpointer import JsonPointer, JsonPointerException


_ST_ADD = 0
_ST_REMOVE = 1


try:
    from collections.abc import MutableMapping, MutableSequence

except ImportError:
    from collections import MutableMapping, MutableSequence
    str = unicode

# Will be parsed by setup.py to determine package metadata
__author__ = 'Stefan Kögl <stefan@skoegl.net>'
__version__ = '1.22'
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


# The "object_pairs_hook" parameter is used to handle duplicate keys when
# loading a JSON object.
_jsonloads = functools.partial(json.loads, object_pairs_hook=multidict)


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
        patch = _jsonloads(patch_str)
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

        builder = DiffBuilder(src, dst)
        ops = list(builder.execute())
        return cls(ops)

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

    @property
    def path(self):
        return '/'.join(self.pointer.parts[:-1])

    @property
    def key(self):
        try:
            return int(self.pointer.parts[-1])
        except ValueError:
            return self.pointer.parts[-1]

    @key.setter
    def key(self, value):
        self.pointer.parts[-1] = str(value)
        self.location = self.pointer.path
        self.operation['path'] = self.location


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

    def _on_undo_remove(self, path, key):
        if self.path == path:
            if self.key >= key:
                self.key += 1
            else:
                key -= 1
        return key

    def _on_undo_add(self, path, key):
        if self.path == path:
            if self.key > key:
                self.key -= 1
            else:
                key -= 1
        return key


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

    def _on_undo_remove(self, path, key):
        if self.path == path:
            if self.key > key:
                self.key += 1
            else:
                key += 1
        return key

    def _on_undo_add(self, path, key):
        if self.path == path:
            if self.key > key:
                self.key -= 1
            else:
                key += 1
        return key


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
            if part not in subobj:
                msg = "can't replace non-existent object '{0}'".format(part)
                raise JsonPatchConflict(msg)
        else:
            raise TypeError("invalid document type {0}".format(type(subobj)))

        subobj[part] = value
        return obj

    def _on_undo_remove(self, path, key):
        return key

    def _on_undo_add(self, path, key):
        return key


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

    @property
    def from_path(self):
        from_ptr = JsonPointer(self.operation['from'])
        return '/'.join(from_ptr.parts[:-1])

    @property
    def from_key(self):
        from_ptr = JsonPointer(self.operation['from'])
        try:
            return int(from_ptr.parts[-1])
        except TypeError:
            return from_ptr.parts[-1]

    @from_key.setter
    def from_key(self, value):
        from_ptr = JsonPointer(self.operation['from'])
        from_ptr.parts[-1] = str(value)
        self.operation['from'] = from_ptr.path

    def _on_undo_remove(self, path, key):
        if self.from_path == path:
            if self.from_key >= key:
                self.from_key += 1
            else:
                key -= 1
        if self.path == path:
            if self.key > key:
                self.key += 1
            else:
                key += 1
        return key

    def _on_undo_add(self, path, key):
        if self.from_path == path:
            if self.from_key > key:
                self.from_key -= 1
            else:
                key -= 1
        if self.path == path:
            if self.key > key:
                self.key -= 1
            else:
                key += 1
        return key


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


class DiffBuilder(object):

    def __init__(self, src, dst):
        self.src = src
        self.dst = dst

        self.ops = []
        self.index_changes = {}

    def insert(self, op):
        self.ops.append(op)

    def execute(self):
        self._compare_values('', None, self.src, self.dst)
        return [op.operation for op in self.ops]

    def _item_added(self, path, key, item, is_sequence):
        if is_sequence:
            key = self.get_index_change(path, key)

        new_op = AddOperation({
            'op': 'add',
            'path': _path_join(path, key),
            'value': item,
        })
        self.insert(new_op)

        if is_sequence:
            self.add_index_change(path, key, +1)

    def _item_moved(self, path, key, item, newkey):
        """ The `item` was moved from `key` to `newkey`

        [a, b, c, d, e]
         0  1, 2, 3, 4

        case 1: move 1 to 3
        [a, c, d, b, e]
         0  1, 2, 3, 4

        """

        key = self.get_index_change(path, key)
        newkey = self.get_index_change(path, newkey)

        if key == newkey:
            return

        new_op = MoveOperation({
            'op': 'move',
            'from': _path_join(path, key),
            'path': _path_join(path, newkey),
        })
        self.insert(new_op)

        self.add_index_change(path, key+1, -1)
        self.add_index_change(path, newkey+1, +1)


    def _item_removed(self, path, key, item, is_sequence):
        if is_sequence:
            key = self.get_index_change(path, key)

        new_op = RemoveOperation({
            'op': 'remove',
            'path': _path_join(path, key),
        })
        self.insert(new_op)

        if is_sequence:
            self.add_index_change(path, key, -1)

    def _item_replaced(self, path, key, item):
        self.insert(ReplaceOperation({
            'op': 'replace',
            'path': _path_join(path, key),
            'value': item,
        }))

    def _compare_dicts(self, path, src, dst):
        src_keys = set(src.keys())
        dst_keys = set(dst.keys())
        added_keys = dst_keys - src_keys
        removed_keys = src_keys - dst_keys

        for key in removed_keys:
            self._item_removed(path, str(key), src[key], False)

        for key in added_keys:
            self._item_added(path, str(key), dst[key], False)

        for key in src_keys & dst_keys:
            self._compare_values(path, key, src[key], dst[key])

    def _compare_lists(self, path, src, dst):
        len_src, len_dst = len(src), len(dst)
        max_len = max(len_src, len_dst)
        min_len = min(len_src, len_dst)
        for key in range(max_len):
            if key < min_len:
                old, new = src[key], dst[key]

                if old == new:
                    continue

                elif isinstance(old, MutableMapping) and \
                    isinstance(new, MutableMapping):
                    self._compare_dicts(_path_join(path, key), old, new)

                elif isinstance(old, MutableSequence) and \
                        isinstance(new, MutableSequence):
                    self._compare_lists(_path_join(path, key), old, new)

                else:
                    self._item_removed(path, key, old, True)
                    self._item_added(path, key, new, True)

            elif len_src > len_dst:
                self._item_removed(path, len_dst, src[key], True)

            else:
                self._item_added(path, key, dst[key], True)

    def _compare_values(self, path, key, src, dst):
        if src == dst:
            return

        elif isinstance(src, MutableMapping) and \
                isinstance(dst, MutableMapping):
            self._compare_dicts(_path_join(path, key), src, dst)

        elif isinstance(src, MutableSequence) and \
                isinstance(dst, MutableSequence):
            self._compare_lists(_path_join(path, key), src, dst)

        else:
            self._item_replaced(path, key, dst)

    def add_index_change(self, path, key, change):
        """ Store the index change of a certain path

        [a, b, c]
         0, 1, 2

        When inserting d at position 1, the indexes of b and c change
        [a, d, b, c]
         0, 1, 2, 3

        add_index_change('/', 1, +1)
        """

        path_changes = self.index_changes.get(path, {})
        key_change = path_changes.get(key, 0)
        key_change = key_change + change
        path_changes[key] = key_change

    def get_index_change(self, path, key):
        path_changes = self.index_changes.get(path, {})
        return path_changes.get(key, 0) + key


def _path_join(path, key):
    if key is None:
        return path

    return path + '/' + str(key).replace('~', '~0').replace('/', '~1')
