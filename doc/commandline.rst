Commandline Utilities
=====================

The JSON patch package contains the commandline utilities ``jsondiff`` and
``jsonpatch``.

``jsondiff``
------------

The program ``jsondiff`` can be used to create a JSON patch by comparing two
JSON files ::

    usage: jsondiff [-h] [--indent INDENT] [-v] FILE1 FILE2

    Diff two JSON files

    positional arguments:
      FILE1
      FILE2

    optional arguments:
      -h, --help       show this help message and exit
      --indent INDENT  Indent output by n spaces
      -v, --version    show program's version number and exit

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
    [{"path": "/a/2", "value": 3, "op": "add"}, {"path": "/b", "op": "remove"}, {"path": "/c", "value": 100, "op": "add"}]

    # show patch with some indentation
    $ jsondiff a.json b.json --indent=2
    [
      {
        "path": "/a/2",
        "value": 3,
        "op": "add"
      },
      {
        "path": "/b",
        "op": "remove"
      },
      {
        "path": "/c",
        "value": 100,
        "op": "add"
      }
    ]



``jsonpatch``
-------------

The program ``jsonpatch`` is used to apply JSON patches on JSON files. ::

    usage: jsonpatch [-h] [--indent INDENT] [-v] ORIGINAL PATCH

    Apply a JSON patch on a JSON files

    positional arguments:
      ORIGINAL         Original file
      PATCH            Patch file

    optional arguments:
      -h, --help       show this help message and exit
      --indent INDENT  Indent output by n spaces
      -v, --version    show program's version number and exit


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

    # c.json now equals b.json
    $ jsondiff b.json c.json
    []

