Commandline Utilities
=====================

The JSON patch package contains the commandline utilities ``jsondiff`` and
``jsonpatch``.

Both utilities read JSON files as UTF-8. When ``jsonpatch`` modifies a file
in-place, it also writes UTF-8.

``jsondiff``
------------

The program ``jsondiff`` can be used to create a JSON patch by comparing two
JSON files ::

    usage: jsondiff [-h] [--indent INDENT] [-u] [-v] FILE1 FILE2

    Diff two JSON files

    positional arguments:
      FILE1
      FILE2

    options:
      -h, --help            show this help message and exit
      --indent INDENT       Indent output by n spaces
      -u, --preserve-unicode
                            Output Unicode character as-is without using Code
                            Point
      -v, --version         show program's version number and exit

Example
^^^^^^^

.. code-block:: bash

    # inspect JSON files
    $ cat a.json
    { "a": [1, 2], "b": 0 }

    $ cat b.json
    { "a": [1, 2, 3], "c": 100 }

    # show patch in "dense" representation
    $ jsondiff a.json b.json
    [{"op": "remove", "path": "/b"}, {"op": "add", "path": "/c", "value": 100}, {"op": "add", "path": "/a/2", "value": 3}]

    # show patch with some indentation
    $ jsondiff a.json b.json --indent=2
    [
      {
        "op": "remove",
        "path": "/b"
      },
      {
        "op": "add",
        "path": "/c",
        "value": 100
      },
      {
        "op": "add",
        "path": "/a/2",
        "value": 3
      }
    ]



``jsonpatch``
-------------

The program ``jsonpatch`` is used to apply JSON patches on JSON files. ::

    usage: jsonpatch [-h] [--indent INDENT] [-b] [-i] [-v] [-u] ORIGINAL [PATCH]

    Apply a JSON patch on a JSON file

    positional arguments:
      ORIGINAL              Original file
      PATCH                 Patch file (read from stdin if omitted)

    options:
      -h, --help            show this help message and exit
      --indent INDENT       Indent output by n spaces
      -b, --backup          Back up ORIGINAL if modifying in-place
      -i, --in-place        Modify ORIGINAL in-place instead of to stdout
      -v, --version         show program's version number and exit
      -u, --preserve-unicode
                            Output Unicode character as-is without using Code
                            Point

Example
^^^^^^^

.. code-block:: bash

    # create a patch
    $ jsondiff a.json b.json > patch.json

    # show the result after applying a patch
    $ jsonpatch a.json patch.json
    {"a": [1, 2, 3], "c": 100}

    $ jsonpatch a.json patch.json --indent=2
    {
      "a": [
        1,
        2,
        3
      ],
      "c": 100
    }

    # pipe result into new file
    $ jsonpatch a.json patch.json --indent=2 > c.json

    # c.json now equals b.json, so there is no difference to print
    $ jsondiff b.json c.json

