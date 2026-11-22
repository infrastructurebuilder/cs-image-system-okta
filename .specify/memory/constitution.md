<!--
Sync Impact Report

Version change: 1.0.0 -> 1.1.0
Bump: MINOR. A principle was materially expanded (Governance: "MINOR when
  a principle or section is added or materially expanded"); no principle
  was removed or redefined.
Amended: 2026-11-22, by the operator ("amend IX"), at spec 001's
  convergence (its T014).
Modified principles: IX. Tests guard behaviour or architecture -- a test
  may also run one of the repository's own release or publish commands to
  show it is accepted, since such a command otherwise runs first when a
  release depends on it (the first 0.2.0 publish failed on one).
Added sections: none. Removed sections: none.

Earlier amendments:
  none -> 1.0.0 (2026-11-22): first ratified constitution, by the operator
    ("make the okta plugin into a speckit-enabled project").
Source: cs-image-system's constitution 1.2.0 (cs-image-system-3,
  .specify/memory/constitution.md), from which this repository's plugin
  moved (spec 008 there). Its users, principles, constraints, workflow and
  governance are carried over and fitted to one identity plugin; where
  this file is silent, that one holds (Governance).
Sections: Users; Core Principles I-X; Additional Constraints; Development
  Workflow; Governance.
-->

# cs-image-system-okta Constitution

## Users

Every specification names which of these it serves.

- **Operators** add and change the groups and users a configuration
  declares, and keep the system's identity working through its CI.
- **An adopting team** starts a configuration repository from a starter
  whose groups are Okta's, and runs the system itself.
- **A plugin author** maintains this plugin, or forks it, and writes it
  against the published kit.
- **Modellers and scientists** are served at one remove: they log into the
  instances whose access this plugin manages, and never touch it.

## Core Principles

### I. Purpose first

The plugin exists so that a configuration's groups and users become the
people who can log into its machines, through Okta, correctly and on the
record. Every specification MUST name the user it serves from the list
above. Work that serves none of them MUST state its reason in its
specification.

Rationale: a named user keeps work pointed at the access people actually
need.

### II. Acceptance is executable

Every specification MUST end in a command or CI job that passes or fails.
A review, a reading or a document is not acceptance. A skipped check is a
failed check: no gate may report success when a leg it depends on did not
run.

Rationale: a gate that skipped and passed lets a release through unproven.

### III. Nothing irreversible by default

A run is a dry run unless told otherwise. The plugin MUST NOT destroy an
Okta or OPA group or user, and no test, tool or job of this repository may
apply an identity root or change anything in Okta or OPA. A live call made
from this repository is read-only, and run only by hand.

Rationale: a destroyed OPA group takes its servers' gid with it, and a
destroyed user takes a person's access; neither comes back.

### IV. The emission is the contract with the past

Generated output for the instance suite's fixture MUST be byte-identical to
its golden unless the change says it moves. A moved golden MUST be read
file by file, never accepted wholesale.

Rationale: the plugin is part of a compiler; its output is its behaviour.

### V. Public by construction

Everything in this repository MUST be safe for the open internet. A
credential is never written to a file, a log or an output; the tests use
dummies, and a secret a workflow needs comes from the platform, never from
the tree. The public-safety scan runs in CI.

Rationale: the repository is public, and so are the configuration
repositories the plugin writes into.

### VI. Layers point one way and plugins do not interfere

The plugin depends only on the system's published SDK (the contract, the
kit and the Terraform libraries), by range, and MUST keep to its declared
surfaces. It MUST NOT import the engine or another provider's plugin. The
provider family the instance suite's machines run on is the suite's alone,
never the plugin's. Installing, loading or testing the plugin MUST NOT
change the behaviour of another.

Rationale: a plugin that reaches past the SDK breaks on the system's next
release, and one that drags a cloud with it cannot be installed without it.

### VII. A budget, and subtraction preferred

Every plan MUST state its expected effect on source lines, test count and
the public surface the plugin uses. Growth in any of them MUST carry a
reason written in the plan. Deleting is a first-class outcome and needs no
further justification.

Rationale: what is not there cannot break.

### VIII. One source per fact

Counts, field tables and version numbers in documents MUST be generated
from the code or be absent. A fact is stated in one owning place and linked
from the others: the Okta builders' fields are this repository's
`docs/CONFIGURATION.md`; everything else of the system is
cs-image-system's own documents, linked by URL.

Rationale: hand-kept facts drift, and a fact kept in two repositories
drifts twice.

### IX. Tests guard behaviour or architecture

A test MUST NOT assert wording, naming, ordering or the prose of a
document. A test that asserts a property of the repository itself is
allowed only when it holds an architectural invariant of Principle VI or a
safety invariant of Principles III to V, or when it runs one of the
repository's own release or publish commands, as the release would run it
but sending nothing anywhere, to show the command is accepted.

Rationale: tests of form fail legitimate refactors and catch no defect a
user would meet. A release command is different: it runs for real only
when a release already depends on it, so a command that is refused stops a
release after its tag (the first 0.2.0 publish did), a defect a user meets.

### X. What a change makes false is part of the change

Every plan MUST list the statements elsewhere that the change makes untrue
(this repository's documents, cs-image-system's documents and starters that
describe the plugin, the reference configuration), and the change MUST
correct them, or name the change in the other repository that will.

Rationale: a plugin in its own repository is described in two places, and
each change opens a seam between them.

## Additional Constraints

- The `Justfile` is the single entry point: `init`, `build`, `test`,
  `full-test`, `release`. `just test` is the local acceptance bar; lint,
  the type check (zero errors) and the tests all block. `just full-test`
  runs before a release.
- Python runs through `uv run python`.
- Everything of the system comes from the package index, by range. Nothing
  here reads another repository's checkout.
- A release is published by trusted publishing from the repository's own
  workflow; no upload token is stored in the repository or its secrets
  (`docs/RELEASING.md`).
- Live testing, when a specification needs it, uses the
  `cs-image-system-testconfig` repository as its configuration, read-only.
  Fast and local tests use the instance suite's fixture.

## Development Workflow

- Work is specified with Spec Kit: a specification (what and why, for a
  named user), then a plan, tasks, implementation and convergence.
- A specification describes changes only. The existing plugin is specified
  by its golden and its tests, not retroactively.
- One feature branch per specification, `feature/<name>` from `develop`,
  finished by a squash-merge with the branch kept. Nothing is committed to
  `main` directly. Nothing is committed or pushed unless the operator asks.
- A specification is **done** when all of the following hold, each shown
  by a command or a record, not by a reading:
  1. Every task in its `tasks.md` is checked, and each has a record of what
     was done and the evidence (a commit, a run, a count).
  2. `/speckit-converge` was run after the last implementation and
     appended nothing, or every task it appended is itself done.
  3. The acceptance it ends in (Principle II) was run at the end and
     passed: its quickstart walked step by step, each result recorded.
  4. Its branch is squash-merged into `develop`, the branch kept.
  5. When its plan names a release, that release is published and every
     run it started passed. When the plan names none, a release that
     carries the specification is still preferred where one is possible;
     if none is cut, the records say why.
  6. Its `spec.md` status line and its row in `specs/README.md` say
     **complete**, with the date.

  Until all six hold, a specification is **in progress**; one that is
  merged but not yet done is **merged**. A step that does not apply is
  named as not applying in its tasks' records rather than left out.

  Rationale: a merge proves the code moved, not that the user was served.
- A defect that does not block a named user waits until its code is
  touched for another reason.

## Governance

This constitution is derived from cs-image-system's constitution (1.2.0).
Where this one is silent, that one holds; where they disagree, this one
holds for this repository, and the difference is named in an amendment.

- **Amendment.** The operator amends the constitution. Each amendment is
  recorded with a version bump: MAJOR when a principle is removed or
  redefined, MINOR when a principle or section is added or materially
  expanded, PATCH for wording.
- **Compliance.** Every plan carries a constitution check against
  Principles I to X. A violation MUST be justified in the plan's complexity
  section, or the plan changes.
- **Review.** A specification is reviewed against Principles I and II
  before it is planned: it names its user and ends in an executable
  acceptance.

**Version**: 1.1.0 | **Ratified**: 2026-11-22 | **Last Amended**: 2026-11-22
