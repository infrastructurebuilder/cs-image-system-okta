# Claude Code Instructions

## Python Execution

Always use `uv run python` instead of `python3` for running Python scripts or commands in this project.

## How Work Is Specified

Work is specified with Spec Kit under `specs/`, governed by `.specify/memory/constitution.md`. Read the constitution before planning or changing anything. Plans live in `specs/<number>-<name>/plan.md`.

## Nothing Reaches Okta, OPA or AWS From A Test

The tests stub every outside service and set dummy credentials. No test, and no command an agent runs, may apply an identity root, change anything in Okta or OPA, or destroy an OPA group or user. The one live call is CI's dispatched, read-only `lookup` job.
