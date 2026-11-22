# SPDX-FileCopyrightText: 2026 Mykel Alvis <mykelalvis@infrastructurebuilder.org>
#
# SPDX-License-Identifier: Apache-2.0

"""Every `uv publish` line of the Publish workflow is one uv accepts.

A publish runs only when a release tag is pushed, so a command line uv
refuses is otherwise found by the release itself, after the tag (the first
0.2.0 tag: `--index` cannot be combined with `--check-url`). Each line is run
here in uv's offline mode, over a stand-in file: uv refuses to publish
offline only after it has parsed its arguments, so that refusal is the proof
the line parses, and nothing reaches an index.
"""
from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
WORKFLOW = REPO / ".github" / "workflows" / "publish.yml"
OFFLINE_REFUSAL = "Unable to publish files in offline mode"


def _publish_lines() -> list[str]:
    jobs = yaml.safe_load(WORKFLOW.read_text())["jobs"]
    return [step["run"] for job in jobs.values() for step in job.get("steps", [])
            if str(step.get("run", "")).startswith("uv publish")]


def test_the_workflow_publishes_to_both_indexes():
    lines = _publish_lines()
    assert any("--index testpypi" in ln for ln in lines) and any("--index pypi" in ln for ln in lines)


@pytest.mark.parametrize("line", _publish_lines())
def test_each_publish_line_parses(tmp_path: Path, line: str):
    uv = shutil.which("uv")
    assert uv, "uv is not on PATH"
    stand_in = tmp_path / "cs_image_system_okta_opa_plugin-0.0.0-py3-none-any.whl"
    stand_in.write_bytes(b"")
    args = [str(stand_in) if a == "dist/*" else a for a in shlex.split(line)[2:]]
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    done = subprocess.run([uv, "publish", "--offline", *args], cwd=REPO, env=env, capture_output=True, text=True)
    assert OFFLINE_REFUSAL in done.stderr, done.stderr
