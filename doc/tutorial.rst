Tutorial
========

Please refer to `RFC 6902 <https://datatracker.ietf.org/doc/html/rfc6902>`_ for the exact
patch syntax.

Creating a Patch
----------------

Patches can be created in two ways. One way is to  explicitly create a
``JsonPatch`` object from an iterable of operation dictionaries, such as a
list, tuple, iterator, or generator. Non-sequence iterables are materialized
before validation so that the patch can be applied repeatedly.
For convenience, the method
``JsonPatch.from_string()`` accepts a string, parses it and constructs the
patch object from it.

.. code-block:: python

    >>> import jsonpatch
    >>> patch = jsonpatch.JsonPatch([
    ...     {'op': 'add', 'path': '/foo', 'value': 'bar'},
    ...     {'op': 'add', 'path': '/baz', 'value': [1, 2, 3]},
    ...     {'op': 'remove', 'path': '/baz/1'},
    ...     {'op': 'test', 'path': '/baz', 'value': [1, 3]},
    ...     {'op': 'replace', 'path': '/baz/0', 'value': 42},
    ...     {'op': 'remove', 'path': '/baz/1'},
    ... ])

    # or equivalently
    >>> patch = jsonpatch.JsonPatch.from_string('''[
    ...     {"op": "add", "path": "/foo", "value": "bar"},
    ...     {"op": "add", "path": "/baz", "value": [1, 2, 3]},
    ...     {"op": "remove", "path": "/baz/1"},
    ...     {"op": "test", "path": "/baz", "value": [1, 3]},
    ...     {"op": "replace", "path": "/baz/0", "value": 42},
    ...     {"op": "remove", "path": "/baz/1"}
    ... ]''')
    >>> patch.apply({})
    {'foo': 'bar', 'baz': [42]}

Another way is to *diff* two objects.

.. code-block:: python

    >>> src = {'foo': 'bar', 'numbers': [1, 3, 4, 8]}
    >>> dst = {'baz': 'qux', 'numbers': [1, 4, 7]}
    >>> patch = jsonpatch.JsonPatch.from_diff(src, dst)

    # or equivalently
    >>> patch = jsonpatch.make_patch(src, dst)


Applying a Patch
----------------

A patch is applied to a JSON document. The patch created by diffing ``src``
and ``dst`` above turns ``src`` into ``dst``:

.. code-block:: python

    >>> result = patch.apply(src)
    >>> result == dst
    True

The ``apply`` method returns a new object as a result. If ``in_place=True`` the
object is modified in place.

The operations of a patch refer to locations in the object it is applied to.
A patch created with ``make_patch(src, dst)`` or ``JsonPatch.from_diff(src,
dst)`` must therefore be applied to ``src`` (or to an object equal to it).
Applying it to any other object, such as ``dst``, usually fails with a
``JsonPatchConflict``, because the locations it refers to don't exist there.
Here it is a ``JsonPatchPathNotFound``, the subclass of ``JsonPatchConflict``
that is raised when the location an operation acts on doesn't exist:

.. code-block:: python

    >>> patch.apply(dst)
    Traceback (most recent call last):
      ...
    jsonpatch.JsonPatchPathNotFound: can't remove a non-existent object 'foo'

Applying it to an object with the same structure but different values may
succeed, though, and overwrite those values. With ``generate_test_ops=True``
each ``remove`` and ``replace`` operation is preceded by a ``test`` operation
that checks the value it removes or replaces. The patch then also records the
previous values, and fails with a ``JsonPatchTestFailed`` if they differ:

.. code-block:: python

    >>> patch = jsonpatch.make_patch({'a': 1, 'b': 2}, {'a': 3},
    ...                              generate_test_ops=True)
    >>> patch.patch  # doctest: +NORMALIZE_WHITESPACE
    [{'op': 'test', 'path': '/b', 'value': 2}, {'op': 'remove', 'path': '/b'},
     {'op': 'test', 'path': '/a', 'value': 1},
     {'op': 'replace', 'path': '/a', 'value': 3}]
    >>> patch.apply({'a': 5, 'b': 2})
    Traceback (most recent call last):
      ...
    jsonpatch.JsonPatchTestFailed: 5 (<class 'int'>) is not equal to tested value 1 (<class 'int'>)

If a patch is only used once, it is not necessary to create a patch object
explicitly.

.. code-block:: python

    >>> obj = {'foo': 'bar'}

    # from a patch string
    >>> patch = '[{"op": "add", "path": "/baz", "value": "qux"}]'
    >>> res = jsonpatch.apply_patch(obj, patch)

    # or from a list
    >>> patch = [{'op': 'add', 'path': '/baz', 'value': 'qux'}]
    >>> res = jsonpatch.apply_patch(obj, patch)


When an Operation Fails
~~~~~~~~~~~~~~~~~~~~~~~

Operations are applied in order. If an operation raises an exception,
application stops. With the default ``in_place=False``, operations affect a
copy, so the original document is unchanged:

.. code-block:: python

    >>> import jsonpatch
    >>> original = {'value': 1}
    >>> patch = [
    ...     {'op': 'replace', 'path': '/value', 'value': 2},
    ...     {'op': 'test', 'path': '/value', 'value': 3},
    ... ]
    >>> try:
    ...     jsonpatch.apply_patch(original, patch)
    ... except jsonpatch.JsonPatchTestFailed:
    ...     print('Test failed')
    Test failed
    >>> original
    {'value': 1}

With ``in_place=True``, the same patch raises ``JsonPatchTestFailed``, but
the earlier replacement remains in the original document. Failed patches
do not roll back changes already made in place:

.. code-block:: python

    >>> try:
    ...     jsonpatch.apply_patch(original, patch, in_place=True)
    ... except jsonpatch.JsonPatchTestFailed:
    ...     print('Test failed')
    Test failed
    >>> original
    {'value': 2}

To get all-or-nothing behaviour without copying the document, pass
``atomic=True`` together with ``in_place=True``. If an operation fails, the
changes of the preceding operations are undone before the exception is
raised, so the document is either fully patched or left unchanged:

.. code-block:: python

    >>> original = {'value': 1}
    >>> try:
    ...     jsonpatch.apply_patch(original, patch, in_place=True, atomic=True)
    ... except jsonpatch.JsonPatchTestFailed:
    ...     print('Test failed')
    Test failed
    >>> original
    {'value': 1}

This only keeps the values that the patch removes or replaces until it has
been applied, so it needs much less memory than ``in_place=False`` for large
documents. The original containers are restored, so references into the
document stay valid. If a patch contains custom operations (see
:class:`jsonpatch.JsonPatch`'s ``operations``), whose changes can't be undone,
the document is copied instead, and its contents are restored from the copy
if an operation fails; nested containers are then replaced by their copies.

Restoring the document exactly, with the same values, the same order of
object members and the same container objects, is guaranteed for documents
made of plain ``dict`` and ``list`` objects, which includes every document
parsed from JSON. Other containers are restored through their own item
operations, which is exact as long as these only change the item they are
given:

* Containers that change when they are merely read, such as a
  ``collections.defaultdict``, which adds a missing key on lookup, are not
  supported: looking up a location, testing a value or reading the ``from``
  of a ``move`` or ``copy`` can add members to them that remain after a
  rollback.
* The copy that patches with custom operations are restored from only
  restores the items of mappings and sequences, not other state that a
  custom operation can change, such as the attributes of objects in the
  document or the ``maps`` of a ``collections.ChainMap``.


Ignoring Missing Locations
~~~~~~~~~~~~~~~~~~~~~~~~~~

`RFC 6902 <https://tools.ietf.org/html/rfc6902#section-4.2>`_ requires a
``remove`` to fail if the location it removes doesn't exist, and this library
follows it: such an operation raises ``JsonPatchPathNotFound``. A ``replace``
of a missing location, and a ``move`` or ``copy`` from one, raise it as well.

.. code-block:: python

    >>> patch = [{'op': 'remove', 'path': '/data/another'}]
    >>> try:
    ...     jsonpatch.apply_patch({'data': {}}, patch)
    ... except jsonpatch.JsonPatchPathNotFound as ex:
    ...     print(ex, ex.op.location)
    can't remove a non-existent object 'another' /data/another

Catching the exception around ``apply`` does not skip just that operation,
though: application stops, and the operations after it are not applied.

If removing a member that is already absent should count as success (an
idempotent ``remove``), the recommended way is a ``JsonPatch`` subclass that
uses its own ``remove`` operation. The ``operations`` attribute of a
``JsonPatch`` class maps each operation name to the class implementing it:

.. code-block:: python

    >>> from types import MappingProxyType
    >>> class IdempotentRemoveOperation(jsonpatch.RemoveOperation):
    ...     def apply(self, obj):
    ...         try:
    ...             return super().apply(obj)
    ...         except jsonpatch.JsonPatchPathNotFound:
    ...             return obj  # nothing to remove
    >>> class IdempotentJsonPatch(jsonpatch.JsonPatch):
    ...     operations = MappingProxyType(dict(
    ...         jsonpatch.JsonPatch.operations,
    ...         remove=IdempotentRemoveOperation,
    ...     ))

    >>> patch = IdempotentJsonPatch([
    ...     {'op': 'remove', 'path': '/data/another'},
    ...     {'op': 'add', 'path': '/data/new', 'value': 1},
    ... ])
    >>> patch.apply({'data': {}})
    {'data': {'new': 1}}

Only a missing member or element is ignored. Other errors still raise, such
as a ``JsonPatchConflict`` for removing the whole document, or a
``JsonPointerException`` if a parent of the location doesn't exist:

.. code-block:: python

    >>> patch = IdempotentJsonPatch([{'op': 'remove', 'path': '/missing/key'}])
    >>> patch.apply({'data': {}})
    Traceback (most recent call last):
      ...
    jsonpointer.JsonPointerException: member 'missing' not found in {'data': {}}

Patches applied this way don't conform to RFC 6902, so only use this where
both sides of an exchange agree on it.


Replacing the Whole Document
----------------------------

A document can be an object, array, string, number, boolean, or ``null``.
An empty ``path`` (``""``) selects the whole document, so a replacement can
also change its type:

.. code-block:: python

    >>> import jsonpatch
    >>> original = {'old': True}
    >>> patch = jsonpatch.JsonPatch([
    ...     {'op': 'replace', 'path': '', 'value': [1, 2]}
    ... ])
    >>> result = patch.apply(original, in_place=True)
    >>> result
    [1, 2]
    >>> original
    {'old': True}

Always use the return value when an operation can replace the root, even
with ``in_place=True``. Replacing the root returns a new value; it cannot
rebind the caller's variable. Changes to members of the original container
can still happen in place.

The empty pointer differs from ``"/"``, which selects an object member
whose key is the empty string:

.. code-block:: python

    >>> jsonpatch.apply_patch({'': 1}, [
    ...     {'op': 'replace', 'path': '/', 'value': 2}
    ... ])
    {'': 2}
    >>> jsonpatch.apply_patch(None, [
    ...     {'op': 'add', 'path': '', 'value': False}
    ... ])
    False


Paths and Special Characters
----------------------------

The ``path`` and ``from`` members of an operation are JSON Pointers
(`RFC 6901 <https://datatracker.ietf.org/doc/html/rfc6901>`_). A pointer is a sequence of
reference tokens, each starting with ``/``, and every token selects one object
key or array index. Because ``/`` separates the tokens, a key that contains
``/`` or ``~`` has to be escaped: ``~`` is written as ``~0`` and ``/`` as
``~1``.

Patches created by ``make_patch`` follow this rule, so a key containing ``/``
shows up escaped in the generated path.

.. code-block:: python

    >>> patch = jsonpatch.make_patch({}, {'/fields/test': '123456'})
    >>> patch.patch
    [{'op': 'add', 'path': '/~1fields~1test', 'value': '123456'}]
    >>> patch.apply({})
    {'/fields/test': '123456'}

The unescaped path ``/fields/test`` would mean something different: the key
``test`` inside the key ``fields``. Applying it to ``{}`` fails, because there
is no key ``fields``.

When writing a patch by hand, escape keys in the same way. ``path_join``
builds a path from a list of unescaped keys and array indices, and
``path_split`` turns a path back into its unescaped parts, for example to
inspect the keys a patch refers to. The parts that ``path_split`` returns are
always strings, also those of array indices.

.. code-block:: python

    >>> jsonpatch.path_join(['/fields/test', 'a~b', 0])
    '/~1fields~1test/a~0b/0'
    >>> jsonpatch.path_split('/~1fields~1test/a~0b/0')
    ('/fields/test', 'a~b', '0')
    >>> [jsonpatch.path_split(op['path']) for op in patch]
    [('/fields/test',)]


Custom Path Syntax
------------------

How paths are read and written is defined by a pointer class, which is
``jsonpointer.JsonPointer`` by default. Another class can be passed as
``pointer_cls`` to ``JsonPatch``, ``JsonPatch.from_string``,
``JsonPatch.from_diff``, ``apply_patch``, ``make_patch``, ``path_split`` and
``path_join``, for example to use a different path syntax.

A pointer stores a path as the list of its unescaped parts, in its ``parts``
attribute. Resolving it against a document only uses these parts, so a class
for a different syntax only has to override three members of ``JsonPointer``:

``__init__(self, pointer)``
    Parses the path string ``pointer`` and sets ``self.parts`` to a list of
    strings, one per object key or array index. The empty list refers to the
    whole document. Raise ``jsonpointer.JsonPointerException`` for an invalid
    path.

``from_parts(cls, parts)``
    A class method that returns a pointer to the given parts, which can also
    contain ints for array indices.

``path``
    A property that turns ``self.parts`` back into a path string. Parts that
    are array indices are strings like ``'0'``. Raise
    ``jsonpointer.JsonPointerException`` if the parts can't be written in the
    syntax.

``path_join`` returns the ``path`` of the pointer that ``from_parts``
returns. ``make_patch`` and ``JsonPatch.from_diff`` write the paths of the
operations they create with it, and the ``path`` and ``from_path`` properties
of operations use it as well.

The following class uses paths like ``a.0.b``, in which the parts are
separated by ``.``. For simplicity, it doesn't support escaping, so it
rejects keys that are empty or contain ``.``, as they could not be told apart
from other paths.

.. code-block:: python

    >>> from jsonpointer import JsonPointer, JsonPointerException

    >>> class DotPointer(JsonPointer):
    ...     """ Paths like 'a.0.b'; '' refers to the whole document """
    ...
    ...     def __init__(self, pointer):
    ...         self.parts = pointer.split('.') if pointer else []
    ...         if '' in self.parts:
    ...             raise JsonPointerException('Empty part in %r' % pointer)
    ...
    ...     @classmethod
    ...     def from_parts(cls, parts):
    ...         pointer = cls('')
    ...         pointer.parts = [str(part) for part in parts]
    ...         return pointer
    ...
    ...     @property
    ...     def path(self):
    ...         for part in self.parts:
    ...             if not part or '.' in part:
    ...                 raise JsonPointerException(
    ...                     'Key %r can not be written as a part' % part)
    ...         return '.'.join(self.parts)

Patches then use this syntax, whether they are written by hand or created by
diffing two documents:

.. code-block:: python

    >>> doc = {'users': [{'name': 'Alice'}]}
    >>> jsonpatch.apply_patch(doc, [
    ...     {'op': 'replace', 'path': 'users.0.name', 'value': 'Bob'},
    ... ], pointer_cls=DotPointer)
    {'users': [{'name': 'Bob'}]}

    >>> patch = jsonpatch.make_patch(
    ...     doc, {'users': [{'name': 'Alice', 'admin': True}]},
    ...     pointer_cls=DotPointer)
    >>> patch.patch
    [{'op': 'add', 'path': 'users.0.admin', 'value': True}]
    >>> patch.apply(doc)
    {'users': [{'name': 'Alice', 'admin': True}]}

    >>> jsonpatch.path_split('users.0.name', pointer_cls=DotPointer)
    ('users', '0', 'name')
    >>> jsonpatch.path_join(['users', 0, 'name'], pointer_cls=DotPointer)
    'users.0.name'

If the class rejects a path or a key, creating or applying the patch fails:

.. code-block:: python

    >>> jsonpatch.make_patch({}, {'a.b': 1}, pointer_cls=DotPointer)
    Traceback (most recent call last):
    ...
    jsonpointer.JsonPointerException: Key 'a.b' can not be written as a part

Such patches are not JSON Patches as defined by RFC 6902, which requires
JSON Pointers. ``path_split`` and ``path_join`` convert them to standard
patches, for example to pass them on to other software:

.. code-block:: python

    >>> def convert_paths(operations, from_cls, to_cls):
    ...     converted = []
    ...     for operation in operations:
    ...         operation = dict(operation)
    ...         for member in ('path', 'from'):
    ...             if member in operation:
    ...                 parts = jsonpatch.path_split(operation[member], from_cls)
    ...                 operation[member] = jsonpatch.path_join(parts, to_cls)
    ...         converted.append(operation)
    ...     return converted

    >>> convert_paths(patch, DotPointer, JsonPointer)
    [{'op': 'add', 'path': '/users/0/admin', 'value': True}]

Override the three members together. If a pointer class doesn't override
``from_parts``, ``path_join`` and thereby ``make_patch`` write JSON Pointers,
as ``from_parts`` of ``JsonPointer`` builds those, whatever syntax the class
reads. This keeps pointer classes working that only change how paths are
resolved, but a class that only overrides ``__init__`` and ``path`` reads the
paths of the patches it creates differently than they were written.


Dealing with Custom Types
-------------------------

Custom JSON dump and load functions can be used to support custom types such as
`decimal.Decimal`. The following examples shows how the
`simplejson <https://simplejson.readthedocs.io/>`_ package, which has native
support for Python's ``Decimal`` type, can be used to create a custom
``JsonPatch`` subclass with ``Decimal`` support:

.. code-block:: python

    >>> import decimal
    >>> import simplejson

    >>> class DecimalJsonPatch(jsonpatch.JsonPatch):
    ...     @staticmethod
    ...     def json_dumper(obj):
    ...         return simplejson.dumps(obj)
    ...
    ...     @staticmethod
    ...     def json_loader(obj):
    ...         return simplejson.loads(obj, use_decimal=True,
    ...                                 object_pairs_hook=jsonpatch.multidict)

    >>> src = {}
    >>> dst = {'bar': decimal.Decimal('1.10')}
    >>> patch = DecimalJsonPatch.from_diff(src, dst)
    >>> doc = {'foo': 1}
    >>> patch.apply(doc)
    {'foo': 1, 'bar': Decimal('1.10')}

Instead of subclassing it is also possible to pass a dump function to
``from_diff``:

.. code-block:: python

    >>> patch = jsonpatch.JsonPatch.from_diff(src, dst, dumps=simplejson.dumps)

a dumps function to ``to_string``:

.. code-block:: python

    >>> serialized_patch = patch.to_string(dumps=simplejson.dumps)
    >>> serialized_patch
    '[{"op": "add", "path": "/bar", "value": 1.10}]'

and load  function to ``from_string``:

.. code-block:: python

    >>> import functools
    >>> loads = functools.partial(simplejson.loads, use_decimal=True,
    ...                           object_pairs_hook=jsonpatch.multidict)
    >>> patch = jsonpatch.JsonPatch.from_string(serialized_patch, loads=loads)
    >>> doc = {'foo': 1}
    >>> patch.apply(doc)
    {'foo': 1, 'bar': Decimal('1.10')}
