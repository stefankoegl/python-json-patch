""" Type checks of typical jsonpatch usage, as seen by a user's type checker.

This file is not run; CI type-checks it with ``mypy --strict`` against the
installed distribution, run from this directory so that the stubs in
jsonpatch-stubs are used rather than jsonpatch.py itself. Lines marked with
``# type: ignore[...]`` must produce exactly that error (strict mode reports
unused ignores), so they test that wrong usage is rejected.
"""

import json
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

import jsonpointer
from jsonpointer import JsonPointer
from typing_extensions import assert_type

import jsonpatch
from jsonpatch import (InvalidJsonPatch, JsonPatch, JsonPatchConflict,
                       JsonPatchException, JsonPatchPathNotFound,
                       JsonPatchTestFailed,
                       PatchOperation)

doc = {'foo': 'bar'}
ops = [{'op': 'add', 'path': '/baz', 'value': 'qux'}]

# module-level functions
assert_type(jsonpatch.apply_patch(doc, ops), Any)
assert_type(jsonpatch.apply_patch(doc, ops, in_place=True), Any)
assert_type(jsonpatch.apply_patch(doc, ops, in_place=True, atomic=True), Any)
assert_type(jsonpatch.apply_patch(doc, json.dumps(ops)), Any)
assert_type(jsonpatch.apply_patch(doc, json.dumps(ops).encode()), Any)
assert_type(jsonpatch.make_patch(doc, {}), JsonPatch)
assert_type(jsonpatch.make_patch(doc, {}, generate_test_ops=True), JsonPatch)

# values of dicts with narrow types are accepted (Mapping is covariant)
str_ops: list[dict[str, str]] = [{'op': 'remove', 'path': '/foo'}]
jsonpatch.apply_patch(doc, str_ops)

# JsonPatch
patch = JsonPatch(ops)
JsonPatch(op for op in ops)
assert_type(patch.apply(doc), Any)
assert_type(patch.apply(doc, in_place=True, atomic=True), Any)
assert_type(patch.to_string(), str)
assert_type(patch.to_string(dumps=json.dumps), str)
assert_type(bool(patch), bool)
assert_type(patch.patch, list[dict[str, Any]])
assert_type(list(patch), list[dict[str, Any]])
assert_type(next(iter(patch)), dict[str, Any])
assert_type(jsonpatch.make_patch(doc, {}).patch, list[dict[str, Any]])
abstract_op: Mapping[str, str] = MappingProxyType({'op': 'remove', 'path': '/foo'})
JsonPatch(iter((abstract_op,)))
assert_type(PatchOperation(abstract_op).operation, dict[str, Any])
assert_type(JsonPatch.from_string('[]'), JsonPatch)
assert_type(JsonPatch.from_string(b'[]', loads=json.loads), JsonPatch)
assert_type(JsonPatch.from_string(bytearray(b'[]')), JsonPatch)
assert_type(JsonPatch.from_diff(doc, {}, optimization=False), JsonPatch)
assert_type(JsonPatch.operations['add'], type[PatchOperation])
assert_type(JsonPatch.operations, MappingProxyType[str, type[PatchOperation]])


class MyPatch(JsonPatch):
    pass


# the alternative constructors return instances of subclasses
assert_type(MyPatch.from_string('[]'), MyPatch)
assert_type(MyPatch.from_diff(doc, {}), MyPatch)

# operations
operation = jsonpatch.AddOperation({'op': 'add', 'path': '/a/0', 'value': 1})
assert_type(operation.apply({'a': []}), Any)
assert_type(operation.location, str)
assert_type(operation.path, str)
assert_type(operation.key, int | str)
operation.key = 1
assert_type(operation.pointer, JsonPointer)
assert_type(operation.operation, dict[str, Any])
move = jsonpatch.MoveOperation({'op': 'move', 'from': '/a', 'path': '/b'})
assert_type(move.from_key, int | str)


# a custom pointer class
class MyPointer(JsonPointer):
    pass


jsonpatch.apply_patch(doc, ops, pointer_cls=MyPointer)
JsonPatch(ops, pointer_cls=MyPointer)

# exceptions
try:
    patch.apply(doc)
except (InvalidJsonPatch, JsonPatchConflict, JsonPatchTestFailed) as ex:
    assert_type(ex, InvalidJsonPatch | JsonPatchConflict | JsonPatchTestFailed)
    failed = ex.op
JsonPatchException('message', op=None)
try:
    patch.apply(doc)
except JsonPatchPathNotFound as ex:
    assert_type(ex, JsonPatchPathNotFound)
    conflict: JsonPatchConflict = ex

# names that jsonpatch re-exports from jsonpointer
try:
    patch.apply(doc)
except jsonpatch.JsonPointerException as ex:
    assert_type(ex, jsonpointer.JsonPointerException)
assert_type(jsonpatch.JsonPointer('/a'), jsonpointer.JsonPointer)

# wrong usage is rejected
jsonpatch.apply_patch(doc, ops, in_place='yes')  # type: ignore[arg-type]
jsonpatch.make_patch(doc)  # type: ignore[call-arg]
JsonPatch(ops).to_string(dumps=len)  # type: ignore[arg-type]
JsonPatch([1, 2])  # type: ignore[list-item]
JsonPatch(ops, pointer_cls=str)  # type: ignore[arg-type]
# apply_patch treats a bytearray as a sequence of operations, and fails
jsonpatch.apply_patch(doc, bytearray(b'[]'))  # type: ignore[arg-type]
