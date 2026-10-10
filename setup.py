#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from setuptools import setup

src = open('jsonpatch.py', encoding='utf-8').read()
metadata = dict(re.findall("__([a-z]+)__ = '([^']+)'", src))
docstrings = re.findall('"""([^"]*)"""', src, re.MULTILINE | re.DOTALL)

PACKAGE = 'jsonpatch'

MODULES = (
        'jsonpatch',
)

REQUIREMENTS = list(open('requirements.txt'))

AUTHOR_EMAIL = metadata['author']
VERSION = metadata['version']
WEBSITE = metadata['website']
LICENSE = metadata['license']
DESCRIPTION = docstrings[0]

# Extract name and e-mail ("Firstname Lastname <mail@example.org>")
AUTHOR, EMAIL = re.match(r'(.*) <(.*)>', AUTHOR_EMAIL).groups()

CLASSIFIERS = [
    'Development Status :: 5 - Production/Stable',
    'Environment :: Console',
    'Intended Audience :: Developers',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3 :: Only',
    'Programming Language :: Python :: 3.10',
    'Programming Language :: Python :: 3.11',
    'Programming Language :: Python :: 3.12',
    'Programming Language :: Python :: 3.13',
    'Programming Language :: Python :: 3.14',
    'Programming Language :: Python :: Implementation :: CPython',
    'Programming Language :: Python :: Implementation :: PyPy',
    'Topic :: Software Development :: Libraries',
    'Topic :: Utilities',
]


setup(name=PACKAGE,
      version=VERSION,
      description=DESCRIPTION,
      long_description=open('README.md', encoding='utf-8').read(),
      long_description_content_type='text/markdown',
      author=AUTHOR,
      author_email=EMAIL,
      license=LICENSE,
      url=WEBSITE,
      py_modules=MODULES,
      package_data={'': ['requirements.txt']},
      scripts=['bin/jsondiff', 'bin/jsonpatch'],
      classifiers=CLASSIFIERS,
      python_requires='>=3.10',
      project_urls={
          'Website': 'https://github.com/stefankoegl/python-json-patch',
          'Repository': 'https://github.com/stefankoegl/python-json-patch.git',
          'Documentation': "https://python-json-patch.readthedocs.org/",
          'PyPI': 'https://pypi.org/pypi/jsonpatch',
          'Tests': 'https://github.com/stefankoegl/python-json-patch/actions',
          'Test Coverage': 'https://coveralls.io/r/stefankoegl/python-json-patch',
      },
      install_requires=REQUIREMENTS,
)
