# Tasks: A release is published with no token anywhere

**Input**: [spec.md](spec.md), [plan.md](plan.md), [quickstart.md](quickstart.md)

Built before this repository used Spec Kit, on 2026-11-22, and written up
here the same day; the tasks below record what was done. The open ones are
the operator's.

## Records

| Task | Record |
| --- | --- |
| T001 | `.github/workflows/publish.yml`: on a pushed `v*` tag, `build` (only in `infrastructurebuilder/cs-image-system-okta`; the tag must equal the plugin's version; `uv build --all-packages`; the files as an artifact), `testpypi` (environment `testpypi`, `id-token: write`, `uv publish --trusted-publishing always --index testpypi --check-url https://test.pypi.org/simple/`), `pypi` (after `testpypi`, for a final version only, environment `pypi`, the same against PyPI). Every action on Node 24 (`upload-artifact@v7`, `download-artifact@v8`, each checked to run `node24`) |
| T002 | `scripts/release`: no token is no longer a refusal; without one the release runs `full-test`, commits only what changed, tags, uploads nothing and says to push the tag; with one it uploads to the index named as before. Every version either index ever listed is refused, whichever index is named, since the tag's push publishes to both |
| T003 | `tests/tooling/test_release_refuses_a_held_version.py`: a version TestPyPI holds refuses a release named for PyPI; the dry form without a token plans the tag and no `uv publish`. 5 passed |
| T004 | `docs/RELEASING.md`: how a release is cut and published; the trust on PyPI, TestPyPI and GitHub, field by field; how to check it and read `invalid-publisher`; a fork: the distribution name and `NAMES`, the workflow's repository, a pending publisher on each index, the environments, and what a new name changes (the namespace, the installation) |
| T005 | The README's "Releasing" and "Documents" and the Justfile's `release` comment say that pushing the tag publishes and link `docs/RELEASING.md` |
| T006 | `just test`: ruff clean, REUSE compliant, pyright 0 errors, the surface check, 188 passed; `publish.yml` parses; `just public-safe` clean over 220 files |
| T008 | 2026-11-22, at the operator's word: `feature/008-trusted-publishing` committed as `084e4bd` and squash-merged into `develop` as `af89e82` (branch kept, pushed); CI on `develop`, [45035158800](https://github.com/infrastructurebuilder/cs-image-system-okta/actions/runs/45035158800), passed: 188 passed, pyright 0 errors, public-safe clean. Then `docs/RELEASING.md` told the index project (`cs-image-system-okta-opa-plugin`) and the repository (`cs-image-system-okta`) apart, the first setup having looked for the repository's name on PyPI: `feature/001-releasing-names`, `c41ba19`, squash-merged as `314c4e5`; CI [45040114558](https://github.com/infrastructurebuilder/cs-image-system-okta/actions/runs/45040114558) passed |
| T010 | 2026-11-22, the first attempt: `v0.2.0` tagged on `314c4e5` and pushed; the Publish run [45040609873](https://github.com/infrastructurebuilder/cs-image-system-okta/actions/runs/45040609873) built both files and stopped at TestPyPI before reaching it: `uv publish` refuses `--index` with `--check-url` (exit 2). Nothing reached either index (neither lists 0.2.0). T012 fixes the workflow |
| T009 | 2026-11-22, by the operator: the trusted publishers on `cs-image-system-okta-opa-plugin` at pypi.org (environment `pypi`) and test.pypi.org (`testpypi`), and the two environments in the repository. TestPyPI's entry first refused the token (`invalid-publisher`; the claims: `infrastructurebuilder/cs-image-system-okta`, `publish.yml`, environment `testpypi`) and was corrected |
| T010 (done) | 2026-11-22: the first tag deleted (no index held 0.2.0) and `v0.2.0` re-cut on `2b740f8` by `just release 0.2.0 pypi` with no token (both indexes free; full-test passed: 191, the low end 71, `standard-aws` 1; nothing to commit). Pushed by the operator; run [45041902604](https://github.com/infrastructurebuilder/cs-image-system-okta/actions/runs/45041902604), after TestPyPI's publisher was corrected and the failed jobs rerun: `build`, `testpypi` and `pypi` passed. **Both indexes list 0.2.0**, each `cs_image_system_okta_opa_plugin-0.2.0-py3-none-any.whl` and `-0.2.0.tar.gz`, uploaded by the workflow, with no upload token created (SC-001, SC-002). Quickstart step 1 was walked as box 2 of the release (the dry form planned the tag and no upload), step 2 is T009, step 3 this run. Recorded in cs-image-system-3's spec 008, T034 |
| T012 | The publish lines drop `--check-url` (`--index` already checks the index it publishes to; `docs/RELEASING.md` and the plan say so); `tests/tooling/test_publish_commands_parse.py` runs every `uv publish` line of the workflow in uv's offline mode over a stand-in file, where uv refuses to publish only after it has parsed the line, so a line it would refuse fails the test, with nothing sent anywhere. Branch `feature/001-publish-index-only` |
| T011 | 2026-11-22: `/speckit-converge`, first pass: every requirement checked against the live state (no secret in the repository; its environments `pypi` and `testpypi`; `uv publish --dry-run --index testpypi` over the published 0.2.0 says "already exists, skipping" for both files, so FR-005 holds; both indexes list 0.2.0), two findings under Constitution IX, appended as T013 and T014. Second pass, after them: nothing appended. Every task checked, the quickstart walked (T010), 0.2.0 published by the run it names; the branch squash-merged into `develop` at this record's merge. The status line and the index row say complete |
| T013 | `test_the_workflow_publishes_to_both_indexes` removed: it asserted the workflow file's text, which Constitution IX forbids; the Publish run shows both indexes (T010) |
| T014 | Constitution 1.0.0 -> 1.1.0, by the operator's word ("amend IX"): Principle IX also allows a test that runs one of the repository's own release or publish commands, as the release would, sending nothing anywhere. `test_each_publish_line_parses` stays, its docstring naming the allowance; `tests/tooling` 7 passed |
| T007 | Spec Kit set up in this repository the same day, on this branch (`specify init --here --integration claude --script py`, 1.2.3, as cs-image-system-3's): its constitution 1.0.0, derived from cs-image-system's 1.2.0; `.claude/CLAUDE.md`; Spec Kit's files under MIT in `REUSE.toml` (`LICENSES/MIT.txt`) |

## Phase 1: Built

- [X] T001 Add the `Publish` workflow in `.github/workflows/publish.yml` (FR-002, FR-003, FR-005, FR-006)
- [X] T002 Let `scripts/release` cut a release with no token and refuse a version either index held (FR-001, FR-004, FR-008)
- [X] T003 [P] Test both in `tests/tooling/test_release_refuses_a_held_version.py`
- [X] T004 [P] Write `docs/RELEASING.md` (FR-007)
- [X] T005 [P] Point `README.md` and `Justfile` at it
- [X] T006 Checkpoint: `just test` and `just public-safe` pass
- [X] T007 Set up Spec Kit and this repository's constitution

## Phase 2: The operator's

- [X] T008 Commit this branch, squash-merge it into `develop` (branch kept) and push; the CI run on `develop` passes
- [X] T009 Register the trusted publishers on PyPI and TestPyPI and create the `testpypi` and `pypi` environments (quickstart step 2; `docs/RELEASING.md`)
- [X] T010 **RELEASE**: walk quickstart steps 1 and 3 for 0.2.0; record the run and both indexes' answer (SC-001); record in cs-image-system-3's spec 008, T034, that 0.2.0 was published by the tag's push
- [X] T012 Drop `--check-url` from the publish lines in `.github/workflows/publish.yml` and test every publish line parses in `tests/tooling/test_publish_commands_parse.py` (found by T010's first attempt)
- [X] T011 Run `/speckit-converge`; then set the status line of `spec.md` and the row in `specs/README.md` to complete, with the date

## Phase 3: Convergence

- [X] T013 CRITICAL: remove `test_the_workflow_publishes_to_both_indexes` from `tests/tooling/test_publish_commands_parse.py`, which asserts the text of a repository file (`--index testpypi`, `--index pypi`) and holds no invariant of Principles III to VI; FR-002's two indexes are shown by the Publish run itself (T010) per Constitution IX (contradicts)
- [X] T014 CRITICAL: settle `test_each_publish_line_parses` in `tests/tooling/test_publish_commands_parse.py` under Constitution IX, which allows a test of a property of the repository itself only for an invariant of Principles III to VI: either the operator amends IX to allow a test that runs one of the repository's own release commands (the defect it guards stopped the first 0.2.0 publish), or the test is removed per Constitution IX (contradicts)
