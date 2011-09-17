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

"""Apply JSON-Patches according to http://tools.ietf.org/html/draft-pbryan-json-patch-01"""

# Will be parsed by setup.py to determine package metadata
__author__ = 'Stefan Kögl <stefan@skoegl.net>'
__version__ = '0.2'
__website__ = 'https://github.com/stefankoegl/python-json-patch'
__license__ = 'Modified BSD License'


import copy
import json


class JsonPatchException(Exception):
    pass


class JsonPatchConflict(JsonPatchException):
    pass


def apply_patch(doc, patch):
    """
    >>> obj = { 'baz': 'qux', 'foo': 'bar' }
    >>> patch = [ { 'remove': '/baz' } ]
    >>> apply_patch(obj, patch)
    {'foo': 'bar'}
    """

    p = JsonPatch(patch)
    return p.apply(doc)


class JsonPatch(object):
    """ A JSON Patch is a list of Patch Operations """

    def __init__(self, patch):
        self.patch = patch

        self.OPERATIONS = {
            'remove': RemoveOperation,
            'add': AddOperation,
            'replace': ReplaceOperation,
        }


    @classmethod
    def from_string(cls, patch_str):
        patch = json.loads(patch_str)
        return cls(patch)


    def apply(self, obj):
        """ Applies the patch to a copy of the given object """

        obj = copy.deepcopy(obj)

        for operation in self.patch:
            op = self._get_operation(operation)
            op.apply(obj)

        return obj


    def _get_operation(self, operation):
        for action, op_cls in self.OPERATIONS.items():
            if action in operation:
                location = operation[action]
                op = op_cls(location, operation)
                return op

        raise JsonPatchException("invalid operation '%s'" % operation)



class PatchOperation(object):
    """ A single operation inside a JSON Patch """

    def __init__(self, location, operation):
        self.location = location
        self.operation = operation


    def locate(self, obj, location, last_must_exist=True):
        """ Walks through the object according to location

        Returns the last step as (sub-object, last location-step) """

        parts = location.split('/')
        if parts.pop(0) != '':
            raise JsonPatchException('location must starts with /')

        for part in parts[:-1]:
            obj, loc_part = self._step(obj, part)

        _, last_loc = self._step(obj, parts[-1], must_exist=last_must_exist)
        return obj, last_loc


    def _step(self, obj, loc_part, must_exist=True):
        """ Goes one step in a locate() call """

        # Its not clear if a location "1" should be considered as 1 or "1"
        # We prefer the integer-variant if possible
        part_variants = self._try_parse(loc_part) + [loc_part]

        for variant in part_variants:
            try:
                return obj[variant], variant
            except:
                continue

        if must_exist:
            raise JsonPatchConflict('key %s not found' % loc_part)
        else:
            return obj, part_variants[0]


    @staticmethod
    def _try_parse(val, cls=int):
        try:
            return [cls(val)]
        except:
            return []


class RemoveOperation(PatchOperation):
    """ Removes an object property or an array element

    >>> obj = { 'baz': 'qux', 'foo': 'bar' }
    >>> patch = JsonPatch( [ { 'remove': '/baz' } ] )
    >>> patch.apply(obj)
    {'foo': 'bar'}

    >>> obj = { 'foo': [ 'bar', 'qux', 'baz' ] }
    >>> patch = JsonPatch( [ { "remove": "/foo/1" } ] )
    >>> patch.apply(obj)
    {'foo': ['bar', 'baz']}
    """

    def apply(self, obj):
        subobj, part = self.locate(obj, self.location)
        del subobj[part]


class AddOperation(PatchOperation):
    """ Adds an object property or an array element

    >>> obj = { "foo": "bar" }
    >>> patch = JsonPatch([ { "add": "/baz", "value": "qux" } ])
    >>> patch.apply(obj)
    {'foo': 'bar', 'baz': 'qux'}

    >>> obj = { "foo": [ "bar", "baz" ] }
    >>> patch = JsonPatch([ { "add": "/foo/1", "value": "qux" } ])
    >>> patch.apply(obj)
    {'foo': ['bar', 'qux', 'baz']}
    """

    def apply(self, obj):
        value = self.operation["value"]
        subobj, part = self.locate(obj, self.location, last_must_exist=False)

        if isinstance(subobj, list):
            if part > len(subobj) or part < 0:
                raise JsonPatchConflict("can't insert outside of list")

            subobj.insert(part, value)

        elif isinstance(subobj, dict):
            if part in subobj:
                raise JsonPatchConflict("object '%s' already exists" % part)

            subobj[part] = value

        else:
            raise JsonPatchConflict("can't add to type '%s'" % subobj.__class__.__name__)


class ReplaceOperation(PatchOperation):
    """ Replaces a value

    >>> obj = { "baz": "qux", "foo": "bar" }
    >>> patch = JsonPatch([ { "replace": "/baz", "value": "boo" } ])
    >>> patch.apply(obj)
    {'foo': 'bar', 'baz': 'boo'}
    """

    def apply(self, obj):
        value = self.operation["value"]
        subobj, part = self.locate(obj, self.location)

        if isinstance(subobj, list):
            if part > len(subobj) or part < 0:
                raise JsonPatchConflict("can't replace outside of list")

        elif isinstance(subobj, dict):
            if not part in subobj:
                raise JsonPatchConflict("can't replace non-existant object '%s'" % part)

        else:
            raise JsonPatchConflict("can't replace in type '%s'" % subobj.__class__.__name__)

        subobj[part] = value
