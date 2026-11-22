# Implementation Plan: A release is published with no token anywhere

**Branch**: `feature/008-trusted-publishing` | **Date**: 2026-11-22 | **Spec**: [spec.md](spec.md)

## Summary

Publishing moves from the operator's machine to a workflow that a pushed
release tag starts. The workflow builds the plugin from the tag and
uploads it by trusted publishing, TestPyPI first and PyPI for a final
version. The release script stops requiring a token: without one it tags
and leaves the upload to the tag's push. A page says how to set the trust
up, and what a fork changes.

## Technical Context

**Language/Version**: Python 3.13; GitHub Actions YAML
**Primary Dependencies**: uv (`uv publish --trusted-publishing always
--index <name>`, which checks the index for files it already holds), `actions/checkout@v5`, `astral-sh/setup-uv@v7`,
`actions/upload-artifact@v7` and `actions/download-artifact@v8` (all on
Node 24)
**Testing**: pytest under the strict session; `tests/tooling` holds the
release script's refusals and its no-token plan
**Target Platform**: GitHub Actions `ubuntu-24.04`; PyPI and TestPyPI
**Project Type**: a single-distribution Python package workspace
**Constraints**: no token in the repository or its secrets; nothing
uploaded from a fork

## Constitution Check

| Principle | How the plan keeps it |
| --- | --- |
| I. Purpose first | serves operators (a release without a token) and a plugin author or fork (setting it up again) |
| II. Acceptance is executable | ends in the `Publish` workflow's run on the first tag, both jobs passing and both indexes listing the version |
| III. Nothing irreversible | publishing changes nothing in Okta or OPA; a version is never cut twice |
| IV. The emission | unchanged; no emitted file moves |
| V. Public by construction | the change removes the one secret a release needed |
| VI. Layers | unchanged; the workflow builds the plugin alone |
| VII. Budget | below |
| VIII. One source | the setup is stated once, in `docs/RELEASING.md`; the README and the Justfile link it |
| IX. Tests | the two new tests hold a safety invariant (a held version is refused; nothing is uploaded without a token's say) |
| X. What it makes false | below |

## Budget

| Measure | Expected | Reason |
| --- | --- | --- |
| Source lines | 0 in the plugin; about +25 in `scripts/release` | the no-token path and the probe of both indexes |
| Tests | +2 (`tests/tooling`) | the refusal by either index, the no-token plan |
| Workflows | +1 (`publish.yml`, about 95 lines) | the publish moves to the tag's push |
| Documents | +1 (`docs/RELEASING.md`) | the setup lives outside the repository and must be written down |
| Public surface the plugin uses | 0 | |

## What the change makes false

- The README's "Releasing" section said the release publishes from the
  operator's machine: corrected.
- The Justfile's `release` comment said the same: corrected.
- cs-image-system-3's spec 008, T034, describes the plugin's 0.2.0 as cut
  with `just release ... pypi` and an upload token: its record of the
  release says it was published by the tag's push (that repository's
  change, at its T034).

## Project Structure

```text
.github/workflows/publish.yml                 # new: the tag's push publishes
scripts/release                               # no token: tag only; both indexes probed
tests/tooling/test_release_refuses_a_held_version.py   # +2 tests
docs/RELEASING.md                             # new: the setup, the check, a fork
README.md, Justfile                           # point at docs/RELEASING.md
```
