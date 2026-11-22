# Quickstart: publishing a release with no token

The acceptance of [spec.md](spec.md). Step 1 is the repository's own;
steps 2 and 3 are the operator's, once.

## Step 1: the release plans no upload without a token

About 1 minute.

```sh
# step 1 -- box 1 of 1 -- v1
cd cs-image-system-okta && unset UV_PUBLISH_TOKEN PYPI_TOKEN TEST_PYPI_TOKEN
just release 0.2.0 pypi yes
```

Expect `published by the tag's push (no token here: ...)` and a dry plan
that names `tag v0.2.0` and no `uv publish`.

## Step 2: the trust, on both indexes and in the repository

Follow [docs/RELEASING.md](../../docs/RELEASING.md), "Setting up trusted
publishing", steps 1 to 3. Expect the publisher listed on each index and
the environments `testpypi` and `pypi` in the repository's settings.

## Step 3: the first publish

About 5 minutes.

```sh
# step 3 -- box 1 of 1 -- v1
cd cs-image-system-okta && just release 0.2.0 pypi && git push origin HEAD v0.2.0
GH_PAGER=cat gh run watch --repo infrastructurebuilder/cs-image-system-okta --exit-status \
  "$(GH_PAGER=cat gh run list --repo infrastructurebuilder/cs-image-system-okta --workflow publish.yml --limit 1 --json databaseId --jq '.[0].databaseId')"
```

Expect the `build`, `testpypi` and `pypi` jobs to pass, and both indexes to
list 0.2.0.
