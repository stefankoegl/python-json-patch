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

"""Apply JSON-Patches according to
http://tools.ietf.org/html/draft-ietf-appsawg-json-patch-03"""

# Will be parsed by setup.py to determine package metadata
__author__ = 'Stefan Kögl <stefan@skoegl.net>'
__version__ = '0.4'
__website__ = 'https://github.com/stefankoegl/python-json-patch'
__license__ = 'Modified BSD License'

import copy
import sys

if sys.version_info < (2, 6):
    import simplejson as json
else:
    import json

if sys.version_info >= (3, 0):
    basestring = (bytes, str)


class JsonPatchException(Exception):
    """Base Json Patch exception"""


class JsonPatchConflict(JsonPatchException):
    """Raised if patch could not be applied due to conflict situation such as:
    - attempt to add object key then it already exists;
    - attempt to operate with nonexistence object key;
    - attempt to insert value to array at position beyond of it size;
    - etc.
    """

class JsonPatchInvalid(JsonPatchException):
    """Raised if patch does not conform to specfication"""


class JsonPointerInvalid(JsonPatchException):
    """Raised if Json Pointer does not conform to specification"""


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
    >>> other = apply_patch(doc, [{'add': '/baz', 'value': 'qux'}])
    >>> doc is not other
    True
    >>> other
    {'foo': 'bar', 'baz': 'qux'}
    >>> apply_patch(doc, [{'add': '/baz', 'value': 'qux'}], in_place=True)
    {'foo': 'bar', 'baz': 'qux'}
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
    ...     {'add': '/foo', 'value': 'bar'},
    ...     {'add': '/baz', 'value': [1, 2, 3]},
    ...     {'remove': '/baz/1'},
    ...     {'test': '/baz', 'value': [1, 3]},
    ...     {'replace': '/baz/0', 'value': 42},
    ...     {'remove': '/baz/1'},
    ... ])
    >>> doc = {}
    >>> patch.apply(doc)
    {'foo': 'bar', 'baz': [42]}

    JsonPatch object is iterable, so you could easily access to each patch
    statement in loop:

    >>> lpatch = list(patch)
    >>> lpatch[0]
    {'add': '/foo', 'value': 'bar'}
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
        self.operations = self.parse_patch(patch)
        self.patch = patch

    def __str__(self):
        """str(self) -> self.to_string()"""
        return self.to_string()

    def __bool__(self):
        return bool(self.patch)

    __nonzero__ = __bool__

    def __iter__(self):
        return iter(self.patch)

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
    def from_diff(cls, src, dst):
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
            if isinstance(value, dict) and isinstance(other, dict):
                for operation in compare_dict(path, value, other):
                    yield operation
            elif isinstance(value, list) and isinstance(other, list):
                for operation in compare_list(path, value, other):
                    yield operation
            else:
                yield {'replace': '/'.join(path), 'value': other}

        def compare_dict(path, src, dst):
            for key in src:
                if key not in dst:
                    yield {'remove': '/'.join(path + [key])}
                    continue
                current = path + [key]
                for operation in compare_values(current, src[key], dst[key]):
                    yield operation
            for key in dst:
                if key not in src:
                    yield {'add': '/'.join(path + [key]), 'value': dst[key]}

        def compare_list(path, src, dst):
            lsrc, ldst = len(src), len(dst)
            for idx in range(min(lsrc, ldst)):
                current = path + [str(idx)]
                for operation in compare_values(current, src[idx], dst[idx]):
                    yield operation
            if lsrc < ldst:
                for idx in range(lsrc, ldst):
                    current = path + [str(idx)]
                    yield {'add': '/'.join(current), 'value': dst[idx]}
            elif lsrc > ldst:
                for idx in reversed(range(ldst, lsrc)):
                    yield {'remove': '/'.join(path + [str(idx)])}

        return cls(list(compare_dict([''], src, dst)))

    def to_string(self):
        """Returns patch set as JSON string."""
        return json.dumps(self.patch)

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

        for operation in self.operations:
            operation.apply(obj)

        return obj

    def parse_patch(self, patch):
        """Convert a json-parsed JSON Patch document into a list of operations

        :param patch: JSON Patch document
        :type patch: list of dicts

        :return: list of PatchOperation objects
        :rtype: list
        """
        if not isinstance(patch, list):
            raise JsonPatchInvalid('JSON patch document must be a list')

        return [self._get_operation(op) for op in patch]

    def _get_operation(self, operation):
        """Return a PatchOperation corresponding to the given operation

        :param operation: a single JSON Patch operation
        :type operation: dict
        """
        for key in operation.keys():
            try:
                op_cls = OP_CLS_MAP[key]
            except KeyError:
                continue
            else:
                return op_cls(operation)
        else:
            raise JsonPatchInvalid("invalid operation '%s'" % operation)


class PatchOperation(object):
    """A single operation inside a JSON Patch."""

    def __init__(self, operation):
        self.operation = self.parse(operation)

    def parse(self, obj):
        raise NotImplementedError('should implement operation parse method')

    def apply(self, obj):
        """Abstract method that applies patch operation to specified object."""
        raise NotImplementedError('should implement operation apply method')


class RemoveOperation(PatchOperation):
    """Removes an object property or an array element."""

    def parse(self, op):
        if op.keys() != ['remove']:
            raise JsonPatchInvalid('Invalid remove operation')
        return {'remove': JsonPointer(op['remove'])}

    def apply(self, obj):
        ptr = self.operation['remove']
        token = ptr.token
        parent_container = ptr.parent.find_value(obj)
        if isinstance(parent_container, list):
            token = int(token)
        del parent_container[token]


class AddOperation(PatchOperation):
    """Adds an object property or an array element."""
    def parse(self, op):
        if set(op.keys()) != set(['add', 'value']):
            raise JsonPatchInvalid('Invalid add operation')
        return {'add': JsonPointer(op['add']), 'value': op['value']}

    def apply(self, obj):
        pointer = self.operation['add']
        parent = pointer.parent.find_value(obj)
        child = pointer.token
        value = self.operation['value']

        if isinstance(parent, list):
            try:
                child = int(child)
            except Exception:
                raise JsonPointerInvalid('trailing token must be integer')
            if child > len(parent) or child < 0:
                raise JsonPatchConflict("can't replace outside of list")
            else:
                parent.insert(child, value)
        elif isinstance(parent, dict):
            if child in parent:
                raise JsonPatchConflict("object '%s' already exists" % child)
            else:
                parent[child] = value


class ReplaceOperation(PatchOperation):
    """Replaces an object property or an array element by new value."""

    def parse(self, op):
        if set(op.keys()) != set(['replace', 'value']):
            raise JsonPatchInvalid('Invalid replace operation')
        return {'replace': JsonPointer(op['replace']), 'value': op['value']}

    def apply(self, obj):
        pointer = self.operation['replace']
        parent = pointer.parent.find_value(obj)
        child = pointer.token
        value = self.operation['value']

        if isinstance(parent, list):
            try:
                child = int(child)
            except Exception:
                raise JsonPointerInvalid('trailing token must be integer')
            if child > len(parent) or child < 0:
                raise JsonPatchConflict("can't replace outside of list")
        elif isinstance(parent, dict):
            if not child in parent:
                raise JsonPatchConflict("can't replace non-existant object '%s'"
                                        "" % child)

        parent[child] = value


class MoveOperation(PatchOperation):
    """Moves an object property or an array element to new location."""

    def parse(self, op):
        if set(op.keys()) != set(['move', 'to']):
            raise JsonPatchInvalid('Invalid move operation')
        return {'move': JsonPointer(op['move']), 'to': JsonPointer(op['to'])}

    def apply(self, obj):
        move = self.operation['move']
        to = self.operation['to']
        value = move.find_value(obj)
        RemoveOperation({'remove': move.to_string()}).apply(obj)
        try:
            AddOperation({'add': to.to_string(), 'value': value}).apply(obj)
        except Exception:
            AddOperation({'add': move.to_string(), 'value': value}).apply(obj)


class TestOperation(PatchOperation):
    """Test value by specified location."""

    def parse(self, op):
        if set(op.keys()) != set(['test', 'value']):
            raise JsonPatchInvalid('Invalid test operation')
        return {'test': JsonPointer(op['test']), 'value': op['value']}

    def apply(self, obj):
        assert self.operation['test'].find_value(obj) == self.operation['value']


OP_CLS_MAP = {
    'remove': RemoveOperation,
    'add': AddOperation,
    'replace': ReplaceOperation,
    'move': MoveOperation,
    'test': TestOperation
}


class JsonPointer(object):

    def __init__(self, ptr):
        self.tokens = self.parse_pointer(ptr)

    @staticmethod
    def parse_pointer(ptr):
        if len(ptr) and not ptr.startswith('/'):
            raise JsonPointerInvalid(ptr)
        tokens = ptr.split('/')[1:]
        tokens = [token.replace('~0', '~') for token in tokens]
        tokens = [token.replace('~1', '/') for token in tokens]
        return tokens

    @staticmethod
    def _lookup(obj, tokens):
        for token in tokens:
            if isinstance(obj, list):
                token = int(token)
            obj = obj[token]
        return obj

    def find_value(self, obj):
        return self._lookup(obj, self.tokens)

    @property
    def token(self):
        return self.tokens[-1]

    def to_string(self):
        tokens = [token.replace('/', '~1') for token in self.tokens]
        tokens = [token.replace('~', '~0') for token in tokens]
        return '/%s' % '/'.join(tokens)

    @property
    def parent(self):
        self_str = self.to_string()
        parent_str = self_str.rsplit('/', 1)[0]
        return JsonPointer(parent_str)
