Releasing jsonpatch
===================

Releases are published to [PyPI](https://pypi.org/project/jsonpatch/) by the
[`Publish to PyPI`](.github/workflows/publish.yaml) GitHub Actions workflow
whenever a GitHub release is published. The workflow authenticates with
[Trusted Publishing](https://docs.pypi.org/trusted-publishers/), so no PyPI API
token needs to be stored as a repository secret.


One-time setup
--------------

### 1. Add a trusted publisher on PyPI

1. Log in to PyPI as an owner of the `jsonpatch` project and open
   <https://pypi.org/manage/project/jsonpatch/settings/publishing/>
   (*Your projects → jsonpatch → Manage → Publishing*).
2. Under *Add a new publisher*, select the **GitHub** tab and enter:

   | Field             | Value               |
   |-------------------|---------------------|
   | Owner             | `stefankoegl`       |
   | Repository name   | `python-json-patch` |
   | Workflow name     | `publish.yaml`      |
   | Environment name  | `pypi`              |

3. Click *Add*.

### 2. Create the `pypi` environment on GitHub

1. In the repository, go to *Settings → Environments → New environment* and
   create an environment named `pypi` (it must match the environment name
   entered on PyPI).
2. Recommended protection rules:
   - **Required reviewers**: add yourself, so every upload waits for a manual
     approval in the Actions tab.
   - **Deployment branches and tags**: choose *Selected branches and tags* and
     add a tag rule `v*`, so only release tags can deploy to PyPI.

### 3. (Optional) TestPyPI for dry runs

To try the full upload without touching the real index:

1. Create an account on <https://test.pypi.org/> (it is separate from PyPI).
2. As `jsonpatch` does not exist on TestPyPI yet, add a *pending* publisher at
   <https://test.pypi.org/manage/account/publishing/> with the same values as
   above, plus *PyPI Project Name* `jsonpatch`, and Environment name
   `testpypi`.
3. Create a GitHub environment named `testpypi` (no tag restriction, since
   manual runs start from a branch).

### 4. Clean up old credentials

Once a release has gone out through the workflow, any PyPI API tokens that were
used for manual uploads (e.g. in `~/.pypirc`) can be revoked at
<https://pypi.org/manage/account/token/>.


Making a release
----------------

1. Update `__version__` in `jsonpatch.py`, commit, and push to `master`.
2. Create a GitHub release whose tag is the version prefixed with `v`
   (e.g. `v1.34` for `__version__ = '1.34'`), targeting `master`. Either use
   *Releases → Draft a new release* in the web UI, or run

       gh release create v1.34 --target master --generate-notes

3. Publishing the release starts the workflow. It
   - fails early if the tag does not match `__version__`,
   - builds the sdist and wheel and checks them with `twine check --strict`,
   - waits for approval if the `pypi` environment requires reviewers,
   - uploads both files to PyPI.

PyPI never accepts the same version twice, so a failed or wrong upload has to
be fixed with a new version number.


Dry runs
--------

*Actions → Publish to PyPI → Run workflow* builds and checks the distributions
from the selected branch without publishing them; the files can be downloaded
from the run's *Artifacts* section. Tick **testpypi** to also upload them to
TestPyPI (requires step 3 of the setup). TestPyPI accepts each version only
once, so re-running for an already uploaded version skips the upload.
