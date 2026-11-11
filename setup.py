import re
from setuptools import setup

with open('jsonpatch.py', encoding='utf-8') as f:
    src = f.read()
metadata = dict(re.findall("__([a-z]+)__ = '([^']+)'", src))
docstrings = re.findall('"""([^"]*)"""', src, re.MULTILINE | re.DOTALL)

PACKAGE = 'jsonpatch'

MODULES = (
        'jsonpatch',
        'jsonpatch_cli',
)

with open('requirements.txt') as f:
    REQUIREMENTS = [line.strip() for line in f if line.strip()]

with open('README.md', encoding='utf-8') as f:
    LONG_DESCRIPTION = f.read()

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
    'Programming Language :: Python :: 3.11',
    'Programming Language :: Python :: 3.12',
    'Programming Language :: Python :: 3.13',
    'Programming Language :: Python :: 3.14',
    'Programming Language :: Python :: Implementation :: CPython',
    'Programming Language :: Python :: Implementation :: PyPy',
    'Topic :: Software Development :: Libraries',
    'Topic :: Utilities',
    'Typing :: Typed',
]


setup(name=PACKAGE,
      version=VERSION,
      description=DESCRIPTION,
      long_description=LONG_DESCRIPTION,
      long_description_content_type='text/markdown',
      author=AUTHOR,
      author_email=EMAIL,
      license_expression=LICENSE,
      url=WEBSITE,
      py_modules=MODULES,
      # jsonpatch is a single-file module, which can't be marked as typed
      # with py.typed (PEP 561), so its type stubs are a stub-only package
      packages=['jsonpatch-stubs'],
      package_data={'jsonpatch-stubs': ['*.pyi']},
      entry_points={
          'console_scripts': [
              'jsondiff = jsonpatch_cli:jsondiff_main',
              'jsonpatch = jsonpatch_cli:jsonpatch_main',
          ]
      },
      classifiers=CLASSIFIERS,
      python_requires='>=3.11',
      project_urls={
          'Website': 'https://github.com/stefankoegl/python-json-patch',
          'Repository': 'https://github.com/stefankoegl/python-json-patch.git',
          'Documentation': 'https://python-json-patch.readthedocs.io/',
          'PyPI': 'https://pypi.org/pypi/jsonpatch',
          'Tests': 'https://github.com/stefankoegl/python-json-patch/actions',
          'Test Coverage': 'https://coveralls.io/github/stefankoegl/python-json-patch',
      },
      install_requires=REQUIREMENTS,
      )
