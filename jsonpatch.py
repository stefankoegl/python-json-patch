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

import bisect
import collections
import copy
import functools
import json
from collections.abc import (Mapping, MutableMapping, MutableSequence,
                             Sequence, Set)
from types import MappingProxyType

from jsonpointer import JsonPointer, JsonPointerException


_ST_ADD = 0
_ST_REMOVE = 1


# Will be parsed by setup.py to determine package metadata
__author__ = 'Stefan Kögl <stefan@skoegl.net>'
__version__ = '1.34'
__website__ = 'https://github.com/stefankoegl/python-json-patch'
__license__ = 'Modified BSD License'


class JsonPatchException(Exception):
    """Base Json Patch exception"""


class InvalidJsonPatch(JsonPatchException):
    """ Raised if an invalid JSON Patch is created """


class JsonPatchConflict(JsonPatchException):
    """Raised if patch could not be applied due to conflict situation such as:
    - attempt to add object key when it already exists;
    - attempt to operate with nonexistence object key;
    - attempt to insert value to array at position beyond its size;
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


def apply_patch(doc, patch, in_place=False, pointer_cls=JsonPointer):
    """Apply list of patches to specified json document.

    :param doc: Document object.
    :type doc: dict

    :param patch: JSON patch as list of dicts or raw JSON-encoded string.
    :type patch: list or str

    :param in_place: While ``True`` patch will modify target document.
                     By default patch will be applied to document copy.
    :type in_place: bool

    :param pointer_cls: JSON pointer class to use.
    :type pointer_cls: Type[JsonPointer]

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

    if isinstance(patch, (str, bytes)):
        patch = JsonPatch.from_string(patch, pointer_cls=pointer_cls)
    else:
        patch = JsonPatch(patch, pointer_cls=pointer_cls)
    return patch.apply(doc, in_place)


def make_patch(src, dst, pointer_cls=JsonPointer):
    """Generates patch by comparing two document objects. Actually is
    a proxy to :meth:`JsonPatch.from_diff` method. The resulting patch
    transforms `src` into `dst`, so it has to be applied to `src` (or to a
    document equal to it).

    :param src: Data source document object.
    :type src: dict

    :param dst: Data target document object.
    :type dst: dict

    :param pointer_cls: JSON pointer class to use.
    :type pointer_cls: Type[JsonPointer]

    >>> src = {'foo': 'bar', 'numbers': [1, 3, 4, 8]}
    >>> dst = {'baz': 'qux', 'numbers': [1, 4, 7]}
    >>> patch = make_patch(src, dst)
    >>> new = patch.apply(src)
    >>> new == dst
    True
    """

    return JsonPatch.from_diff(src, dst, pointer_cls=pointer_cls)


class PatchOperation(object):
    """A single operation inside a JSON Patch."""

    def __init__(self, operation, pointer_cls=JsonPointer):
        self.pointer_cls = pointer_cls

        if not operation.__contains__('path'):
            raise InvalidJsonPatch("Operation must have a 'path' member")

        if isinstance(operation['path'], self.pointer_cls):
            self.location = operation['path'].path
            self.pointer = operation['path']
        else:
            self.location = operation['path']
            try:
                self.pointer = self.pointer_cls(self.location)
            except TypeError:
                raise InvalidJsonPatch("Invalid 'path'")

        self.operation = operation

    def apply(self, obj):
        """Abstract method that applies a patch operation to the specified object."""
        raise NotImplementedError('should implement the patch operation.')

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
        return self.get_part(-1)

    @key.setter
    def key(self, value):
        self.set_part(-1, value)

    def get_part(self, index):
        try:
            return int(self.pointer.parts[index])
        except ValueError:
            return self.pointer.parts[index]

    def set_part(self, index, value):
        self.pointer.parts[index] = str(value)
        self.location = self.pointer.path
        self.operation['path'] = self.location


class RemoveOperation(PatchOperation):
    """Removes an object property or an array element."""

    def apply(self, obj):
        subobj, part = _to_last(self.pointer, obj)

        if isinstance(subobj, Sequence) and not isinstance(part, int):
            raise JsonPointerException("invalid array index '{0}'".format(part))

        try:
            del subobj[part]
        except (KeyError, IndexError):
            msg = "can't remove a non-existent object '{0}'".format(part)
            raise JsonPatchConflict(msg)

        return obj


class AddOperation(PatchOperation):
    """Adds an object property or an array element."""

    def apply(self, obj):
        try:
            value = self.operation["value"]
        except KeyError:
            raise InvalidJsonPatch(
                "The operation does not contain a 'value' member")

        # Insert a copy so the document does not share mutable values with
        # the patch; otherwise later operations would modify the patch itself.
        return self._add(obj, copy.deepcopy(value))

    def _add(self, obj, value):
        subobj, part = _to_last(self.pointer, obj)

        if isinstance(subobj, MutableSequence):
            if part is None:
                return value  # we're replacing the root

            elif part == '-':
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
            if part is None:
                raise TypeError("invalid document type {0}".format(type(subobj)))
            else:
                raise JsonPatchConflict("unable to fully resolve json pointer {0}, part {1}".format(self.location, part))
        return obj


class ReplaceOperation(PatchOperation):
    """Replaces an object property or an array element by a new value."""

    def apply(self, obj):
        try:
            value = self.operation["value"]
        except KeyError:
            raise InvalidJsonPatch(
                "The operation does not contain a 'value' member")

        # copied for the same reason as in AddOperation.apply
        value = copy.deepcopy(value)

        subobj, part = _to_last(self.pointer, obj)

        if part is None:
            return value

        if part == "-":
            raise InvalidJsonPatch("'path' with '-' can't be applied to 'replace' operation")

        if isinstance(subobj, MutableSequence):
            if part >= len(subobj) or part < 0:
                raise JsonPatchConflict("can't replace outside of list")

        elif isinstance(subobj, MutableMapping):
            if part not in subobj:
                msg = "can't replace a non-existent object '{0}'".format(part)
                raise JsonPatchConflict(msg)
        else:
            if part is None:
                raise TypeError("invalid document type {0}".format(type(subobj)))
            else:
                raise JsonPatchConflict("unable to fully resolve json pointer {0}, part {1}".format(self.location, part))

        subobj[part] = value
        return obj


class MoveOperation(PatchOperation):
    """Moves an object property or an array element to a new location."""

    def apply(self, obj):
        try:
            if isinstance(self.operation['from'], self.pointer_cls):
                from_ptr = self.operation['from']
            else:
                from_ptr = self.pointer_cls(self.operation['from'])
        except KeyError:
            raise InvalidJsonPatch(
                "The operation does not contain a 'from' member")

        subobj, part = _to_last(from_ptr, obj)
        try:
            value = subobj[part]
        except (KeyError, IndexError) as ex:
            raise JsonPatchConflict(str(ex))

        # If source and target are equal, this is a no-op
        if self.pointer == from_ptr:
            return obj

        if isinstance(subobj, MutableMapping) and \
                self.pointer.contains(from_ptr):
            raise JsonPatchConflict('Cannot move values into their own children')

        obj = RemoveOperation({
            'op': 'remove',
            'path': self.operation['from']
        }, pointer_cls=self.pointer_cls).apply(obj)

        # the value has been detached from its old location, so no copy needed
        obj = AddOperation({
            'op': 'add',
            'path': self.location,
        }, pointer_cls=self.pointer_cls)._add(obj, value)

        return obj

    @property
    def from_path(self):
        from_ptr = self.pointer_cls(self.operation['from'])
        return '/'.join(from_ptr.parts[:-1])

    @property
    def from_key(self):
        return self.get_from_part(-1)

    @from_key.setter
    def from_key(self, value):
        self.set_from_part(-1, value)

    def get_from_part(self, index):
        from_ptr = self.pointer_cls(self.operation['from'])
        try:
            return int(from_ptr.parts[index])
        except ValueError:
            return from_ptr.parts[index]

    def set_from_part(self, index, value):
        from_ptr = self.pointer_cls(self.operation['from'])
        from_ptr.parts[index] = str(value)
        self.operation['from'] = from_ptr.path


class TestOperation(PatchOperation):
    """Test value by specified location."""

    def apply(self, obj):
        try:
            subobj, part = _to_last(self.pointer, obj)
            if part is None:
                val = subobj
            else:
                val = self.pointer.walk(subobj, part)
        except JsonPointerException as ex:
            raise JsonPatchTestFailed(str(ex))

        try:
            value = self.operation['value']
        except KeyError:
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
            from_ptr = self.pointer_cls(self.operation['from'])
        except KeyError:
            raise InvalidJsonPatch(
                "The operation does not contain a 'from' member")

        subobj, part = _to_last(from_ptr, obj)
        try:
            value = copy.deepcopy(subobj if part is None else subobj[part])
        except (KeyError, IndexError) as ex:
            raise JsonPatchConflict(str(ex))

        # value is already a deep copy, no need to copy it again
        obj = AddOperation({
            'op': 'add',
            'path': self.location,
        }, pointer_cls=self.pointer_cls)._add(obj, value)

        return obj


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

    JsonPatch object is iterable, so you can easily access each patch
    statement in a loop:

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
    json_dumper = staticmethod(json.dumps)
    json_loader = staticmethod(_jsonloads)

    operations = MappingProxyType({
        'remove': RemoveOperation,
        'add': AddOperation,
        'replace': ReplaceOperation,
        'move': MoveOperation,
        'test': TestOperation,
        'copy': CopyOperation,
    })

    def __init__(self, patch, pointer_cls=JsonPointer):
        self.patch = patch
        self.pointer_cls = pointer_cls

        # Verify that the structure of the patch document
        # is correct by retrieving each patch element.
        # Much of the validation is done in the initializer
        # though some is delayed until the patch is applied.
        for op in self.patch:
            # We're only checking for strings in the following check
            # for two reasons:
            #
            # - It should come from JSON, which only allows strings as
            #   dictionary keys, so having a string here unambiguously means
            #   someone used: {"op": ..., ...} instead of [{"op": ..., ...}].
            #
            # - There's no possible false positive: if someone give a sequence
            #   of mappings, this won't raise.
            if isinstance(op, (str, bytes)):
                raise InvalidJsonPatch("Document is expected to be sequence of "
                                       "operations, got a sequence of strings.")

            self._get_operation(op)

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
    def from_string(cls, patch_str, loads=None, pointer_cls=JsonPointer):
        """Creates JsonPatch instance from string source.

        :param patch_str: JSON patch as raw string.
        :type patch_str: str

        :param loads: A function of one argument that loads a serialized
                      JSON string.
        :type loads: Callable

        :param pointer_cls: JSON pointer class to use.
        :type pointer_cls: Type[JsonPointer]

        :return: :class:`JsonPatch` instance.
        """
        json_loader = loads or cls.json_loader
        patch = json_loader(patch_str)
        return cls(patch, pointer_cls=pointer_cls)

    @classmethod
    def from_diff(
            cls, src, dst, optimization=True, dumps=None,
            pointer_cls=JsonPointer,
    ):
        """Creates JsonPatch instance based on comparison of two document
        objects. Json patch would be created for `src` argument against `dst`
        one. The resulting patch transforms `src` into `dst`, so it has to be
        applied to `src` (or to a document equal to it).

        :param src: Data source document object.
        :type src: dict

        :param dst: Data target document object.
        :type dst: dict

        :param dumps: A function of one argument that produces a serialized
                      JSON string.
        :type dumps: Callable

        :param pointer_cls: JSON pointer class to use.
        :type pointer_cls: Type[JsonPointer]

        :return: :class:`JsonPatch` instance.

        >>> src = {'foo': 'bar', 'numbers': [1, 3, 4, 8]}
        >>> dst = {'baz': 'qux', 'numbers': [1, 4, 7]}
        >>> patch = JsonPatch.from_diff(src, dst)
        >>> new = patch.apply(src)
        >>> new == dst
        True
        """
        json_dumper = dumps or cls.json_dumper
        builder = DiffBuilder(src, dst, json_dumper, pointer_cls=pointer_cls)
        builder._compare_values((), None, src, dst)
        ops = list(builder.execute())
        return cls(ops, pointer_cls=pointer_cls)

    def to_string(self, dumps=None):
        """Returns patch set as JSON string."""
        json_dumper = dumps or self.json_dumper
        return json_dumper(self.patch)

    @property
    def _ops(self):
        return tuple(map(self._get_operation, self.patch))

    def apply(self, obj, in_place=False):
        """Applies the patch to a given object.

        :param obj: Document object.
        :type obj: dict

        :param in_place: Tweaks the way how patch would be applied - directly to
                         specified `obj` or to its copy.
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

        if not isinstance(op, (str, bytes)):
            raise InvalidJsonPatch("Operation's op must be a string")

        if op not in self.operations:
            raise InvalidJsonPatch("Unknown operation {0!r}".format(op))

        cls = self.operations[op]
        return cls(operation, pointer_cls=self.pointer_cls)


class DiffBuilder(object):

    def __init__(self, src_doc, dst_doc, dumps=json.dumps, pointer_cls=JsonPointer):
        self.dumps = dumps
        self.pointer_cls = pointer_cls
        self.index_storage = [{}, {}]
        self.index_storage2 = [{}, {}]
        self.__root = root = []
        self.src_doc = src_doc
        self.dst_doc = dst_doc
        # the _ArrayItems of each array, by the location of the array
        self.arrays = {}
        root[:] = [root, root, None]

    def store_index(self, value, index, st):
        typed_key = (value, type(value))
        try:
            storage = self.index_storage[st]
            stored = storage.get(typed_key)
            if stored is None:
                storage[typed_key] = [index]
            else:
                storage[typed_key].append(index)

        except TypeError:
            # unhashable values are grouped by a key that equal values share
            storage = self.index_storage2[st]
            storage.setdefault(_hashable(typed_key), []).append(
                (typed_key, index))

    def take_index(self, value, st):
        typed_key = (value, type(value))
        try:
            stored = self.index_storage[st].get(typed_key)
            if stored:
                return stored.pop()

        except TypeError:
            storage = self.index_storage2[st].get(_hashable(typed_key), [])
            for i in range(len(storage)-1, -1, -1):
                if storage[i][0] == typed_key:
                    return storage.pop(i)[1]

    def insert(self, op):
        root = self.__root
        last = root[0]
        last[1] = root[0] = [last, root, op]
        return root[0]

    def remove(self, index):
        link_prev, link_next, _ = index
        link_prev[1] = link_next
        link_next[0] = link_prev
        index[:] = []

    def __iter__(self):
        root = self.__root
        curr = root[1]
        while curr is not root:
            yield curr[2]
            curr = curr[1]

    def execute(self):
        operations = list(self._replay())
        i = 0
        while i < len(operations):
            if i + 1 < len(operations):
                op_first, op_second = operations[i], operations[i + 1]
                if op_first['path'] == op_second['path'] and \
                        op_first['op'] == 'remove' and \
                        op_second['op'] == 'add':
                    yield {
                        'op': 'replace',
                        'path': _to_pointer(op_second['path']),
                        'value': op_second['value'],
                    }
                    i += 2
                    continue

            operation = operations[i]
            for member in ('from', 'path'):
                if member in operation:
                    operation[member] = _to_pointer(operation[member])
            yield operation
            i += 1

    def _replay(self):
        """ Applies the operations to the arrays of the source document, and
        returns them with the array indices at which they apply """
        for items in self.arrays.values():
            items.reset()

        for op in self:
            operation = dict(op)
            # 'from' is removed before 'path' is added
            if 'from' in op:
                operation['from'] = self._parts(op['from'])
                self._set_present(op['from'], False)

            operation['path'] = self._parts(op['path'])
            if op['op'] == 'remove':
                self._set_present(op['path'], False)
            elif op['op'] in ('add', 'move'):
                self._set_present(op['path'], True)

            yield operation

    def _array_items(self, location):
        """ The _ArrayItems of the array at location """
        items = self.arrays.get(location)
        if items is None:
            items = self.arrays[location] = _ArrayItems()
        return items

    def _location(self, parts):
        """ The location of parts in the current document """
        location = ()
        for part in parts:
            if isinstance(part, int):
                part = self._array_items(location).at(part)
            location += (part,)
        return location

    def _new_location(self, path, key):
        """ The location of an item inserted at key of the container at path
        of the current document """
        location = self._location(path)
        if isinstance(key, int):
            key = self._array_items(location).insert(key)
        return _path_join(location, key)

    def _parts(self, location):
        """ The parts of location in the current document. If location is an
        array item that is not in the array, its index is where it would be
        if it was. """
        return tuple(part.index() if isinstance(part, _ArrayItem) else part
                     for part in location)

    def _set_present(self, location, present):
        """ Adds the array item at location to the current document, or
        removes it, if not present """
        item = location[-1] if location else None
        if isinstance(item, _ArrayItem):
            if present:
                item.array.add(item)
            else:
                item.array.remove(item)

    def _item_added(self, path, key, item):
        target = _path_join(path, key)
        index = self.take_index(item, _ST_REMOVE)
        if index is not None:
            removed = index[2]['path']
            # where the removed item is if it is not removed
            source = self._parts(removed)
            # RFC 6902 does not allow moving a value into its own children
            if not _is_inside(target, source):
                self.remove(index)
                if source != target:
                    self.insert({'op': 'move', 'from': removed,
                                 'path': self._new_location(path, key)})
                else:
                    # the removed item stays where the added one would be
                    self._set_present(removed, True)
                return

        new_index = self.insert({'op': 'add',
                                 'path': self._new_location(path, key),
                                 'value': item})
        self.store_index(item, new_index, _ST_ADD)

    def _item_removed(self, path, key, item):
        source = _path_join(path, key)
        location = self._location(source)
        index = self.take_index(item, _ST_ADD)
        if index is not None:
            added_location = index[2]['path']
            added = self._parts(added_location)
            moved_from = _without_item(source, added)
            target = _item_after(added, source, False)
            # RFC 6902 does not allow moving a value into its own children
            if not _is_inside(target, moved_from):
                self.remove(index)
                if moved_from != target:
                    self._set_present(location, False)
                    self.insert({'op': 'move', 'from': location,
                                 'path': added_location})
                else:
                    # the removed item stays where the added one would be
                    self._set_present(added_location, False)
                return

        self._set_present(location, False)
        new_index = self.insert({'op': 'remove', 'path': location})
        self.store_index(item, new_index, _ST_REMOVE)

    def _item_replaced(self, path, key, item):
        self.insert({
            'op': 'replace',
            'path': self._location(_path_join(path, key)),
            'value': item,
        })

    def _compare_dicts(self, path, src, dst):
        added_keys = [key for key in dst if key not in src]
        removed_keys = [key for key in src if key not in dst]
        intersection = [key for key in src if key in dst]

        for key in removed_keys:
            self._item_removed(path, str(key), src[key])

        for key in added_keys:
            self._item_added(path, str(key), dst[key])

        for key in intersection:
            self._compare_values(path, str(key), src[key], dst[key])

    def _compare_lists(self, path, src, dst):
        len_src, len_dst = len(src), len(dst)
        max_len = max(len_src, len_dst)
        min_len = min(len_src, len_dst)
        for key in range(max_len):
            if key < min_len:
                old, new = src[key], dst[key]
                if isinstance(old, MutableMapping) and \
                        isinstance(new, MutableMapping):
                    self._compare_dicts(_path_join(path, key), old, new)

                elif isinstance(old, MutableSequence) and \
                        isinstance(new, MutableSequence):
                    self._compare_lists(_path_join(path, key), old, new)

                # To ensure we catch changes to JSON, we can't rely on a
                # simple old == new, because it would not recognize the
                # difference between 1 and True, among other things.
                elif self.dumps(old) == self.dumps(new):
                    continue

                else:
                    self._item_removed(path, key, old)
                    self._item_added(path, key, new)

            elif len_src > len_dst:
                self._item_removed(path, len_dst, src[key])

            else:
                self._item_added(path, key, dst[key])

    def _compare_values(self, path, key, src, dst):
        if isinstance(src, MutableMapping) and \
                isinstance(dst, MutableMapping):
            self._compare_dicts(_path_join(path, key), src, dst)

        elif isinstance(src, MutableSequence) and \
                isinstance(dst, MutableSequence):
            self._compare_lists(_path_join(path, key), src, dst)

        # To ensure we catch changes to JSON, we can't rely on a simple
        # src == dst, because it would not recognize the difference between
        # 1 and True, among other things. Using json.dumps is the most
        # fool-proof way to ensure we catch type changes that matter to JSON
        # and ignore those that don't. The performance of this could be
        # improved by doing more direct type checks, but we'd need to be
        # careful to accept type changes that don't matter when JSONified.
        elif self.dumps(src) == self.dumps(dst):
            return

        else:
            self._item_replaced(path, key, dst)


# The DiffBuilder works with parts, which are tuples of object keys (str) and
# array indices (int), and with locations, in which _ArrayItem objects take
# the place of array indices. Operations keep locations: when a move replaces
# an earlier 'add' or 'remove', the array indices in the operations after it
# change, but their locations do not.


class _ArrayItem(object):
    """ An item that an array has at some point of the diff """

    __slots__ = ('array', 'label', 'initial')

    def __init__(self, array, label, initial):
        self.array = array
        self.label = label
        # if the item is in the array of the source document
        self.initial = initial

    def index(self):
        """ The index of the item in the array, or the index it would have if
        it was in the array """
        return bisect.bisect_left(self.array.present_labels, self.label)


class _ArrayItems(object):
    """ All items that an array has at some point of the diff, and the items
    that it has at the moment, both ordered by their labels.

    The array has its items in this order at every point of the diff, also
    when a move later replaces the 'add' or 'remove' of an item. So an item
    inserted at an index is put directly after the item before it in the
    array: inserting at the index of a removed item inserts before it, if a
    move replaces its 'remove' later. """

    # how far apart the labels of items inserted one after the other are
    step = 1 << 16
    # how far apart labels are at the start and at the ends
    gap = 1 << 32

    def __init__(self):
        self.items = []
        self.labels = []
        self.present = []
        self.present_labels = []

    def at(self, index):
        """ The item at index of the array """
        # the items of the source document follow the items that the diff
        # has dealt with, so they are only created when needed
        while len(self.present) <= index:
            label = self.labels[-1] + self.gap if self.labels else 0
            item = _ArrayItem(self, label, True)
            self.items.append(item)
            self.labels.append(label)
            self.present.append(item)
            self.present_labels.append(label)

        return self.present[index]

    def insert(self, index):
        """ Inserts a new item at index of the array, and returns it """
        position = 0
        if index:
            position = bisect.bisect_right(self.labels,
                                           self.at(index - 1).label)

        if position == 0 or position == len(self.labels):
            if not self.labels:
                label = 0
            elif position == 0:
                label = self.labels[0] - self.gap
            else:
                label = self.labels[-1] + self.gap

        else:
            if self.labels[position] - self.labels[position - 1] < 2:
                self._relabel()
            low, high = self.labels[position - 1], self.labels[position]
            label = low + min(self.step, (high - low) // 2)

        item = _ArrayItem(self, label, False)
        self.items.insert(position, item)
        self.labels.insert(position, label)
        self.add(item)
        return item

    def _relabel(self):
        self.labels = [i * self.gap for i in range(len(self.items))]
        for item, label in zip(self.items, self.labels):
            item.label = label
        self.present_labels = [item.label for item in self.present]

    def add(self, item):
        """ Adds item to the array """
        position = bisect.bisect_left(self.present_labels, item.label)
        self.present.insert(position, item)
        self.present_labels.insert(position, item.label)

    def remove(self, item):
        """ Removes item from the array """
        position = bisect.bisect_left(self.present_labels, item.label)
        del self.present[position]
        del self.present_labels[position]

    def reset(self):
        """ Changes the array back to its items in the source document """
        self.present = [item for item in self.items if item.initial]
        self.present_labels = [item.label for item in self.present]


def _hashable(value):
    """ A hashable value that is equal for equal values """
    if isinstance(value, Mapping):
        return frozenset((key, _hashable(item)) for key, item in value.items())

    if isinstance(value, Set):
        return frozenset(_hashable(item) for item in value)

    if isinstance(value, (bytes, bytearray)):
        return bytes(value)

    if isinstance(value, Sequence) and not isinstance(value, str):
        return tuple(_hashable(item) for item in value)

    try:
        hash(value)
    except TypeError:
        # other unhashable values share one key
        return None

    return value


def _path_join(path, key):
    if key is None:
        return path

    return path + (key,)


def _to_pointer(path):
    return ''.join('/' + str(part).replace('~', '~0').replace('/', '~1')
                   for part in path)


def _is_prefix(sub_parts, parts):
    return sub_parts == parts[:len(sub_parts)]


def _is_inside(parts, container):
    return len(parts) > len(container) and _is_prefix(container, parts)


def _shift(parts, depth, offset):
    return parts[:depth] + (parts[depth] + offset,) + parts[depth + 1:]


def _without_item(parts, location):
    """ Changes parts, which assumes that there is an item at location, to
    the item missing """
    depth = len(location) - 1
    if isinstance(location[-1], int) and _is_inside(parts, location[:-1]) \
            and parts[depth] > location[-1]:
        return _shift(parts, depth, -1)

    return parts


def _item_after(location, parts, inserted):
    """ Where the item at location is after inserting (or removing, if not
    inserted) the value at parts """
    depth = len(parts) - 1
    if not isinstance(parts[-1], int) or not _is_inside(location, parts[:-1]):
        return location

    if inserted and location[depth] >= parts[-1]:
        return _shift(location, depth, 1)

    if not inserted and location[depth] > parts[-1]:
        return _shift(location, depth, -1)

    return location


def _to_last(pointer, doc):
    """Resolve pointer like JsonPointer.to_last, without indexing into strings.

    RFC 6901 only allows reference tokens to be applied to objects and arrays,
    but older versions of jsonpointer treat strings as sequences.
    """
    subobj, part = pointer.to_last(doc)

    if part is not None and isinstance(subobj, str):
        raise JsonPointerException(
            "Cannot apply token '{0}' to non-container type {1}".format(
                part, type(subobj)))

    return subobj, part
