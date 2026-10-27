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
        {'op': 'add', 'path': '/foo', 'value': 'bar'},
        {'op': 'add', 'path': '/baz', 'value': [1, 2, 3]},
        {'op': 'remove', 'path': '/baz/1'},
        {'op': 'test', 'path': '/baz', 'value': [1, 3]},
        {'op': 'replace', 'path': '/baz/0', 'value': 42},
        {'op': 'remove', 'path': '/baz/1'},
    ])

    # or equivalently
    >>> patch = jsonpatch.JsonPatch.from_string('[{"op": "add", ....}]')

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
``JsonPatchConflict``, because the locations it refers to don't exist there:

.. code-block:: python

    >>> patch.apply(dst)
    Traceback (most recent call last):
      ...
    jsonpatch.JsonPatchConflict: can't remove a non-existent object 'foo'

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

When writing a patch by hand, escape keys in the same way. The ``jsonpointer``
package, which ``jsonpatch`` depends on, can build a pointer from a list of
unescaped keys.

.. code-block:: python

    >>> from jsonpointer import JsonPointer
    >>> JsonPointer.from_parts(['/fields/test', 'a~b']).path
    '/~1fields~1test/a~0b'


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
            @staticmethod
            def json_dumper(obj):
                return simplejson.dumps(obj)

            @staticmethod
            def json_loader(obj):
                return simplejson.loads(obj, use_decimal=True,
                                        object_pairs_hook=jsonpatch.multidict)

    >>> src = {}
    >>> dst = {'bar': decimal.Decimal('1.10')}
    >>> patch = DecimalJsonPatch.from_diff(src, dst)
    >>> doc = {'foo': 1}
    >>> result = patch.apply(doc)
    {'foo': 1, 'bar': Decimal('1.10')}

Instead of subclassing it is also possible to pass a dump function to
``from_diff``:

    >>> patch = jsonpatch.JsonPatch.from_diff(src, dst, dumps=simplejson.dumps)

a dumps function to ``to_string``:

    >>> serialized_patch = patch.to_string(dumps=simplejson.dumps)
    '[{"op": "add", "path": "/bar", "value": 1.10}]'

and load  function to ``from_string``:

    >>> import functools
    >>> loads = functools.partial(simplejson.loads, use_decimal=True,
                                  object_pairs_hook=jsonpatch.multidict)
    >>> patch.from_string(serialized_patch, loads=loads)
    >>> doc = {'foo': 1}
    >>> result = patch.apply(doc)
    {'foo': 1, 'bar': Decimal('1.10')}
