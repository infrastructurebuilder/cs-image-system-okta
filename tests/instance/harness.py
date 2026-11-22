# SPDX-FileCopyrightText: 2026 Mykel Alvis <mykelalvis@infrastructurebuilder.org>
#
# SPDX-License-Identifier: Apache-2.0

"""The instance suite's harness: a stubbed run over a private copy of the
suite's own fixture (``tests/instance/fixture``), through the published test
kit (``cs_image_system.system.testing``), with the plugin's own stubs
(``cs_image_system.okta_opa_plugin.testing``), the AWS stubs its machines run
on (``aws_stubs``) and the Terraform roots library's standing in for the
outside world.

It keeps the names the tests used in cs-image-system-3's shared harness, from
which they moved (spec 008), so each test reads as it did there:
``FixtureRun``, ``copy_config``, ``stub_environment``, ``load_context`` and the
rest. Nothing here reaches Okta, OPA or AWS.
"""
from __future__ import annotations

import os
import re
import shutil
from pathlib import Path
from typing import Any

import aws_stubs
from aws_stubs import VENDOR_AMI, VPCS, record_network_facts

from cs_image_system.hashicorp_utils.testing import BareRun, bare_run
from cs_image_system.okta_opa_plugin import testing as okta_testing
from cs_image_system.system import testing as kit
from cs_image_system.system.testing import (
    FIXED_CHECKED_AT,
    FIXED_NOW,
    FIXED_RUN_ID,
    FIXED_TIMESTAMP,
    cli_context,
    command_lines,
    drive_lifecycles,
    load_context,
    module_path,
    modules_beside,
    modules_inside,
    os_type_for_family,
    passing_session,
    tree,
)
from cs_image_system.tofu_roots import testing as roots_testing

__all__ = [
    "FIXED_CHECKED_AT",
    "FIXED_NOW",
    "FIXED_RUN_ID",
    "FIXED_TIMESTAMP",
    "FIXTURE_CONFIG",
    "FIXTURE_TEAM",
    "REPO",
    "VENDOR_AMI",
    "VPCS",
    "BareRun",
    "FixtureRun",
    "bare_run",
    "cli_context",
    "command_lines",
    "copy_config",
    "drive_lifecycles",
    "load_context",
    "module_path",
    "modules_beside",
    "modules_inside",
    "os_type_for_family",
    "passing_session",
    "plain",
    "private_plugin_cache",
    "record_network_facts",
    "stub_environment",
    "tree",
]

REPO = Path(__file__).resolve().parents[2]
FIXTURE_CONFIG = REPO / "tests" / "instance" / "fixture"     # the suite's own; no run ever applies it

#: the OPA team the fixture's Okta builders name, as its credential variables spell it
FIXTURE_TEAM = "nos_coastal_modeling_cloud_sandbox"


def copy_config(tmp_path: Path, name: str = "config") -> Path:
    """A private copy of the suite's fixture, its apply flags off and its
    runtimes non-ephemeral (the kit's copy), with the network facts record an
    offline load adopts."""
    dst = kit.copy_fixture(FIXTURE_CONFIG, tmp_path, name)
    record_network_facts(dst)
    return dst


def plain(value: Any) -> Any:
    """The plaintext of a fixture value that may be an ``ENC[age:...]``
    marker, opened with the fixture's TEST identity."""
    return kit.plain(value, FIXTURE_CONFIG / kit.IDENTITY_FILE)


def stub_environment(monkeypatch) -> list[str]:
    """The core's stubs (tools journaled, never run; the clock and ``USER``
    pinned), the plugin's (dummy credentials for the fixture's team; groups
    present, the server registry empty, retirements journaled), the AWS stubs
    and the Terraform roots library's; the command journal is returned, the
    relabels and the retirements the stubs made are on
    ``stub_environment.retags`` and ``.retirements``."""
    retags: list[tuple[str, dict[str, str]]] = []
    retirements: list[tuple[str, str]] = []
    journal = kit.stub_core(monkeypatch, FIXTURE_CONFIG / kit.IDENTITY_FILE, stubs=(
        lambda mp: okta_testing.credentials(mp, (FIXTURE_TEAM,)),
        lambda mp: aws_stubs.stub(mp, retags),
        roots_testing.stub,
        lambda mp: okta_testing.stub(mp, retirements),
    ))
    stub_environment.retags = retags  # type: ignore[attr-defined]
    stub_environment.retirements = retirements  # type: ignore[attr-defined]
    return journal


class FixtureRun:
    """One prepared copy of the suite's fixture and its loaded context;
    ``run()`` drives lifecycles."""

    def __init__(self, tmp_path: Path, monkeypatch, dry_run: bool = True, config_root: Path | None = None,
                 overlays: list[Path] | None = None, undeclare: list[str] | None = None):
        self.journal = stub_environment(monkeypatch)
        self.retags: list[tuple[str, dict[str, str]]] = getattr(stub_environment, "retags", [])
        self.config_root = config_root or copy_config(tmp_path)
        self._cwd = os.getcwd()
        self.ctx = load_context(self.config_root, dry_run=dry_run, overlays=overlays, undeclare=undeclare)
        self.generated = self.config_root / "generated"
        self.meta_state = self.config_root / "meta-state"

    def run(self, lifecycles: list[str] | str = "all", *, apply: bool = True, commit: bool = False,
            state_query: bool = False, only: list[str] | None = None,
            force_bake: list[str] | None = None):
        return drive_lifecycles(self.ctx, lifecycles, apply=apply, commit=commit, state_query=state_query,
                                only=only, force_bake=force_bake)

    def restore_cwd(self) -> None:
        os.chdir(self._cwd)


def private_plugin_cache(tmp_path: Path, roots: list[Path]) -> Path:
    """A private OpenTofu provider cache under ``tmp_path`` for a test that
    runs the real ``tofu`` (``TF_PLUGIN_CACHE_DIR`` is not safe under
    concurrent ``init``), seeded by COPYING the providers the roots require
    from the shared cache when one is there."""
    private = tmp_path / "plugin-cache"
    private.mkdir(exist_ok=True)
    shared = os.environ.get("TF_PLUGIN_CACHE_DIR")
    if not shared or not Path(shared).is_dir():
        return private
    sources: set[str] = set()
    for r in roots:
        for tf in r.rglob("*.tf"):
            for src in re.findall(r'source\s*=\s*"([^"]+)"', tf.read_text()):
                if src.startswith((".", "/")) or ":" in src:      # a module path or URL
                    continue
                parts = src.split("/")
                if len(parts) == 2:
                    parts = ["registry.opentofu.org", *parts]
                if len(parts) == 3:
                    sources.add("/".join(parts))
    for src in sorted(sources):
        have = Path(shared) / src
        if have.is_dir() and not (private / src).exists():
            shutil.copytree(have, private / src)
    return private
