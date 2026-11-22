# Specifications

Work on the Okta plugin is specified here with Spec Kit, under the
[constitution](../.specify/memory/constitution.md). A specification says
what changes and why, for a named user, and ends in an acceptance that a
command or a CI job can pass or fail. The plugin as it arrived from
cs-image-system-3 (spec 008 there) is not specified here; its golden and its
tests describe it.

## Written

| Specification | Serves | Ends in | State |
| --- | --- | --- | --- |
| [001 A release is published with no token anywhere](001-trusted-publishing/spec.md) | operators; a plugin author, and whoever forks the repository | a pushed release tag publishing the plugin to TestPyPI, then PyPI, with no upload token stored or exported | complete 2026-11-22: 0.2.0 published by it to TestPyPI and PyPI, converged ([tasks](001-trusted-publishing/tasks.md)) |

A specification's state is one of `written`, `planned`, `in progress`,
`merged` and `complete`; it is `complete` only when the constitution's
definition of done holds (Development Workflow), and `merged` until then.

## Working on a specification

`/speckit-clarify` to settle open points, `/speckit-plan`,
`/speckit-tasks`, `/speckit-implement`, then `/speckit-converge`. One
feature branch per specification, `feature/<name>` from `develop`.
