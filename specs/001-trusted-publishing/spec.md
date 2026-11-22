# Feature Specification: A release is published with no token anywhere

**Feature Directory**: `specs/001-trusted-publishing`

**Feature Branch**: `feature/008-trusted-publishing` (started before this repository used Spec Kit, under cs-image-system-3's spec 008 name; kept by the operator's word, 2026-11-22)

**Created**: 2026-11-22

**Status**: Complete 2026-11-22 (0.2.0 published by it to TestPyPI and PyPI; converged)

**Input**: User description: "There's no publish token for pypi. Tell me how to make a trusted publisher (b). Make sure this is documented in case someone forks this repo. Make the okta plugin into a speckit-enabled project and write the publish thing above as a spec that's basically already done. Don't do this in a different branch."

**Users served**: operators (who cut a release and should need no upload
token to do it); a plugin author, and whoever forks this repository (who
must be able to set the same publishing up again, under a name of their
own).

## Why

The plugin's first release from this repository, 0.2.0, could not be cut:
the release script uploaded from the operator's machine, and that needs an
upload token for the index, which the operator does not keep. A long-lived
token is also a secret to store, guard and rotate, in a repository whose
rule is that nothing in it is secret.

The package indexes offer **trusted publishing** instead: an index is told,
once, to accept uploads for a project from one GitHub repository, one
workflow file and one GitHub environment. The workflow proves who it is
with a short-lived token GitHub issues to the job. Nothing long-lived
exists, anywhere.

Two things have to hold for that to be usable. The release must not need a
token at all, and the setup must be written down well enough to be done
again, by a new maintainer, after a repository move, or by someone who
forks the repository and cannot publish under this project's name.

## Clarifications

### Session 2026-11-22

- Q: How is the first release published without a token? → A: By trusted
  publishing (the operator chose it over a hand-made token or a repository
  secret)
- Q: Must a fork be able to follow it? → A: Yes; it is documented for a
  fork, which publishes under a name of its own
- Q: Which branch carries it? → A: The branch it was built on,
  `feature/008-trusted-publishing`, with Spec Kit set up in the same branch

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A release with no token (Priority: P1)

An operator cuts a release with `just release <version> pypi` and pushes
the tag. The plugin is published to TestPyPI and then PyPI, and at no point
does anyone create, store or export an upload token.

**Why this priority**: it is the release the plugin cannot have today.

**Independent Test**: with no token in the environment, the release's dry
form plans a tag and no upload; the real form tags after `full-test`; the
tag's push runs the `Publish` workflow, whose TestPyPI and PyPI jobs pass,
and both indexes list the version.

**Acceptance Scenarios**:

1. **Given** no upload token in the environment, **When** the operator runs
   the release, **Then** it refuses nothing for want of a token, runs
   `full-test`, commits only what changed, tags `v<version>`, uploads
   nothing, and says to push the tag.
2. **Given** that tag pushed, **When** the `Publish` workflow runs, **Then**
   it builds from the tag, refuses a tag that is not the plugin's version,
   publishes to TestPyPI, and then, for a final version, to PyPI.
3. **Given** a version either index has ever listed, **When** the operator
   runs the release, **Then** it is refused before anything changes, naming
   the index.
4. **Given** files an index already holds (an earlier upload by hand, a
   rerun), **When** the workflow publishes, **Then** they are skipped, not
   uploaded twice.

---

### User Story 2 - The trust can be set up again from the documents (Priority: P2)

A maintainer who has never done it sets up trusted publishing on PyPI,
TestPyPI and the repository from `docs/RELEASING.md` alone.

**Why this priority**: the setup lives outside the repository, on the
indexes and in the repository's settings; without the page it is lost.

**Independent Test**: following the page's four steps, the first tagged
release publishes; the page names every field and value it needs, how to
check the result, and what an `invalid-publisher` failure means.

**Acceptance Scenarios**:

1. **Given** the page, **When** a maintainer registers the publisher on
   each index and creates the two environments, **Then** the next pushed
   tag publishes with no further change.

---

### User Story 3 - A fork can publish under a name of its own (Priority: P3)

Someone forks the repository. Their tag pushes publish nothing until they
make the publishing their own, and the page says exactly what that takes.

**Why this priority**: a fork cannot publish under this project's name,
and must not try.

**Independent Test**: in a fork, a pushed tag skips the `Publish`
workflow's jobs; the page lists the changes a fork makes (the distribution
name, the repository the workflow names, a pending publisher on each index,
the two environments) and what a new name changes for a configuration (the
plugin's namespace, its installation).

**Acceptance Scenarios**:

1. **Given** a fork that changed nothing, **When** it pushes a tag,
   **Then** the workflow's jobs are skipped and nothing is uploaded.
2. **Given** a fork that made the page's changes, **When** it pushes a tag,
   **Then** its plugin is published under its own name.

### Edge Cases

- A token is present after all: the release uploads to the index named
  from the operator's machine, and the workflow then finds those files and
  skips them.
- A development version (`.dev`, `a`, `b`, `rc`): TestPyPI alone.
- A renamed repository, workflow file or environment: the index refuses
  (`invalid-publisher`) until its publisher entry is changed to match.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A release MUST be cut with no upload token present: tagged
  after `full-test`, with nothing uploaded from the operator's machine.
- **FR-002**: A pushed `v<version>` tag MUST publish that version to
  TestPyPI and, for a final version, then PyPI, by trusted publishing, with
  no token stored in the repository or its secrets.
- **FR-003**: A tag that is not the plugin's version MUST be refused by the
  workflow before anything is built.
- **FR-004**: A version either index ever listed MUST be refused by the
  release before anything changes.
- **FR-005**: A file an index already holds MUST be skipped, not uploaded
  twice.
- **FR-006**: The workflow MUST publish only from this repository; a fork's
  tag publishes nothing until the fork names itself.
- **FR-007**: `docs/RELEASING.md` MUST say how a release is cut and
  published, how to set up trusted publishing on each index and in the
  repository, how to check it, and what a fork must change, including what
  a new distribution name changes for a configuration.
- **FR-008**: With a token present, the release MUST still be able to
  upload from the operator's machine, as before.

### Key Entities

- **A trusted publisher**: an index's record that a repository, a workflow
  file and an environment may publish a project.
- **A release tag**: `v<version>`, the one trigger of a publish.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The plugin's 0.2.0 is listed on TestPyPI and PyPI, published
  by the workflow, with zero upload tokens created for it.
- **SC-002**: Zero secrets are added to the repository for publishing.
- **SC-003**: A fork's tag push uploads zero files.

## Assumptions

- The operator is an Owner of `cs-image-system-okta-opa-plugin` on both
  PyPI and TestPyPI, and an administrator of the repository on GitHub.
- The project already exists on both indexes (its 0.1.x came from
  cs-image-system-3), so its publishers are added to the project, not as
  pending publishers.
