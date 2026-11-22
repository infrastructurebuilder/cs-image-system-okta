# SPDX-FileCopyrightText: 2026 Mykel Alvis <mykelalvis@infrastructurebuilder.org>
#
# SPDX-License-Identifier: Apache-2.0

"""The `standard-aws` starter, whose groups are the Okta plugin's, with the
plugin from this checkout and the system and the AWS family from the index.

A `full-test` leg (scripts/full-test-legs), never part of `just test`
(pyproject.toml's `norecursedirs` leaves this directory out): the
starter is rendered by the installed system's own `init-config`, as an
adopting team's tree is, then loaded, validated and dry-run through every
lifecycle with nothing reaching AWS, Okta or OPA (the network answers come
from the tree's own declarations; the Okta credentials a load checks for are
dummies, since a load only reads that they are set: spec 008, T003).
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import yaml
from harness import drive_lifecycles, load_context, record_network_facts, stub_environment

from cs_image_system.contract.names import super_safe_name
from cs_image_system.engine.commands.run_lifecycles import validate_only

STARTER = "standard-aws"


def _render(tmp_path: Path) -> Path:
    root = tmp_path / STARTER
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    subprocess.run(["cs-image-system", "init-config", str(root), "--from", STARTER], check=True, env=env,
                   capture_output=True, text=True)
    return root


def _builders(root: Path, key: str) -> list[dict]:
    out: list[dict] = []
    for p in sorted((root / "cfg").glob("*.y*ml")):
        doc = yaml.safe_load(p.read_text()) or {}
        out.extend(b for b in doc.get(key) or [] if isinstance(b, dict))
    return out


def _stub_the_trees_own_world(monkeypatch, root: Path) -> None:
    """AWS discovery answered from the tree's own networks, the vendor image
    queries answered, and dummy credentials for every Okta team it names."""
    from cs_image_system.aws_runtime import aws_utils

    class _AnySecurityGroups(dict):
        def __contains__(self, key: object) -> bool:
            return True

    vpcs = {"default"} | {str((r.get("networking") or {}).get("network") or "default")
                          for r in _builders(root, "runtime_builders") if r.get("type") == "aws"}
    monkeypatch.setattr(aws_utils, "get_vpc_map_and_default_vpc_id",
                        lambda session_config: ({v: {"subnets": []} for v in vpcs}, "default", _AnySecurityGroups()))
    for b in _builders(root, "group_builders") + _builders(root, "user_builders"):
        if b.get("team"):
            team = super_safe_name(str(b["team"]))
            monkeypatch.setenv(f"TF_VAR_{team}_key", "dummy")
            monkeypatch.setenv(f"TF_VAR_{team}_secret", "dummy")
    record_network_facts(root)


def test_the_standard_aws_starter_validates_and_dry_runs_every_lifecycle(tmp_path, monkeypatch):
    root = _render(tmp_path)
    cwd = os.getcwd()
    try:
        stub_environment(monkeypatch)
        _stub_the_trees_own_world(monkeypatch, root)
        ctx = load_context(root, dry_run=True)
        assert validate_only(ctx) == []
        assert {type(gb).__module__.split(".")[1] for gb in ctx.group_builders.values()} >= {"okta_opa_plugin"}
        summary = drive_lifecycles(ctx, "all", apply=False)
        assert summary.ok, summary.error
        assert any((root / "generated" / "identity").rglob("*.tf")), "no Okta identity root was emitted"
    finally:
        os.chdir(cwd)
