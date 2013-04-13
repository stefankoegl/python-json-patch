Tutorial
========

Please refer to `RFC 6902 <http://tools.ietf.org/html/rfc6902>`_ for the exact
patch syntax.

Creating a Patch
----------------

Patches can be created in two ways. One way is to  explicitly create a
``JsonPatch`` object from a list of operations. For convenience, the method
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

A patch is always applied to an object.

.. code-block:: python

    >>> doc = {}
    >>> result = patch.apply(doc)
    {'foo': 'bar', 'baz': [42]}

The ``apply`` method returns a new object as a result. If ``in_place=True`` the
object is modified in place.

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
