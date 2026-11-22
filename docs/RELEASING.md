# Releasing the Okta plugin

A release of `cs-image-system-okta-opa-plugin` takes two commands and no
secret:

```sh
just release <part|version> pypi    # full-test, then a commit and the tag v<version>
git push origin HEAD v<version>     # the tag's push publishes it
```

The first runs on the operator's machine. It checks that the version is new
on both indexes, runs `just full-test`, builds, commits if anything changed,
and tags. The second hands the tag to GitHub, and the `Publish` workflow
([.github/workflows/publish.yml](../.github/workflows/publish.yml)) uploads
the build to TestPyPI and then, for a final version, to PyPI.

No upload token is involved. The workflow uses **trusted publishing**: each
index has been told to accept uploads for this project from one GitHub
repository, one workflow file and one GitHub environment. The workflow proves
it is that workflow with a short-lived token GitHub issues to the job, so
there is no long-lived token to store, leak or rotate. This page says how
that trust is set up, so it can be set up again: by a new maintainer, after
a repository move, or by someone who forks this repository.

`just release 0.2.0 pypi yes` is the dry form: it says what it would do and
changes nothing.

## How the release decides where to upload

- **No token in the environment (the usual case):** the script uploads
  nothing. It tags, and the tag's push publishes.
- **A token in the environment** (`UV_PUBLISH_TOKEN`, or `PYPI_TOKEN` /
  `TEST_PYPI_TOKEN` for the index named): the script uploads to the index
  named itself, before tagging. The workflow still runs on the tag's push,
  finds those files already on the index and skips them
  (`uv publish --check-url`), and uploads only what is missing.

Either way, a version either index has ever listed is refused before
anything changes. An index never takes a second build under a version it
held, even a deleted one, so a version is never cut twice.

## Setting up trusted publishing

This is done once per index, by someone who is an **Owner** of the project on
that index. It needs no change to the repository: the workflow is already
written for it.

### 1. On PyPI

1. Sign in to [pypi.org](https://pypi.org) as an Owner of
   `cs-image-system-okta-opa-plugin`.
2. Open **Your projects**, find the project, and choose **Manage**.
3. Choose **Publishing** in the project's menu.
4. Under **Add a new publisher**, choose the **GitHub** tab and fill in:

   | Field | Value |
   | --- | --- |
   | Owner | `infrastructurebuilder` |
   | Repository name | `cs-image-system-okta` |
   | Workflow name | `publish.yml` |
   | Environment name | `pypi` |

5. Choose **Add**. The publisher is listed under the project's publishers.

### 2. On TestPyPI

TestPyPI is a separate site with its own accounts and its own trust. Do the
same at [test.pypi.org](https://test.pypi.org), with one difference:

| Field | Value |
| --- | --- |
| Environment name | `testpypi` |

The owner, repository name and workflow name are the same as for PyPI.

### 3. On GitHub

The environment names above must exist in the repository, because the index
checks the environment the job ran in.

1. In the repository on GitHub, open **Settings**, then **Environments**.
2. Choose **New environment**, name it `testpypi`, and choose **Configure
   environment**.
3. Do the same for `pypi`.
4. Optional, and recommended for `pypi`:
   - **Required reviewers**: name yourself, so every PyPI upload waits for
     your approval in the workflow run, after TestPyPI has taken it.
   - **Deployment branches and tags**: choose **Selected branches and tags**
     and add the tag rule `v*`, so only a release tag can use the
     environment.

Neither environment needs a secret.

### 4. Check it

Push a tag for a version that is new on both indexes, then watch the run:

```sh
GH_PAGER=cat gh run list --repo infrastructurebuilder/cs-image-system-okta --workflow publish.yml --limit 1
```

The `testpypi` job publishes first. The `pypi` job runs after it, and only
for a final version. A job that fails with `invalid-publisher` names the
claim the index did not recognise; compare it with the four fields above. A
repository, workflow file or environment that was renamed needs its
publisher entry changed to match.

## If you fork this repository

A fork can build and test everything as it is: CI needs no secret. It cannot
publish under this project's name, which belongs to the upstream project's
owners on both indexes. The `Publish` workflow therefore runs only in the
upstream repository (the `if: github.repository == ...` line of its `build`
job), so a fork's tag push does nothing until the fork makes it its own.

To release a fork under a name of its own:

1. **Choose a new distribution name** and write it in
   `packages/okta-opa-plugin/pyproject.toml` (`[project] name`) and in
   `NAMES` in [scripts/release](../scripts/release).
   - The name decides the plugin's **namespace**: the qualified form of its
     builder words. Today `cs-image-system-okta-opa-plugin` gives
     `okta-opa`, so a tree may write `okta-opa/okta-tf`. A new name gives a
     new namespace, and a tree that wrote the old qualified words must write
     the new ones (`tests/instance/test_qualified_words.py` names them).
     Bare words (`okta-tf`) are unaffected.
   - The system's `okta` extra (`cs-image-system[okta]`) installs the
     upstream plugin by its name. A fork's plugin is installed by its own
     name instead, for example
     `uv tool install cs-image-system --with <your-name>`.
2. **Point the workflow at the fork**: change the repository named in the
   `if:` line of `.github/workflows/publish.yml` to `<you>/<your-repo>`.
3. **Register a pending publisher on each index.** A project that does not
   exist yet is set up from your account rather than from a project: on
   pypi.org, open **Your account**, then **Publishing**, then **Add a new
   pending publisher**. Fill in your new project name, your GitHub owner
   and repository, `publish.yml` and `pypi`. Do the same on test.pypi.org
   with `testpypi`. The first upload creates the project, with you as its
   owner, and turns the pending publisher into a normal one.
4. **Create the `testpypi` and `pypi` environments** in your repository, as
   in step 3 above.
5. **Release**: `just release <version> pypi`, then push the tag.

If you would rather upload with a token than set up trusted publishing,
export it as `UV_PUBLISH_TOKEN` (or `PYPI_TOKEN` / `TEST_PYPI_TOKEN`) when you
run `just release`. The script then uploads from your machine, and the
workflow, once pointed at your fork, only checks what is already there.
