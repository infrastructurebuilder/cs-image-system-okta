# SPDX-FileCopyrightText: 2026 Mykel Alvis <mykelalvis@infrastructurebuilder.org>
#
# SPDX-License-Identifier: Apache-2.0

"""The Okta cases of cs-image-system-3's ``tests/test_login_proof.py``
(spec 008, T020): the login proof over `sft ssh`, as the plugin offers it.

An expired client session is named, not silent; without an OPA token the
enrolled client logs in and the record says so; a group without workload
names has nothing to prove; the workload facts come from the builder; as
the workload the client is handed the team and the address. The client is
stubbed at `run_sft` (in the plugin's `sft_login`); the registry and the
power state at the builder seams.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from harness import FixtureRun

from cs_image_system.contract.power_state import RUNNING  # the contract's, which the kit re-exports
from cs_image_system.engine.commands import login_proof as lp
from cs_image_system.okta_opa_plugin import sft_login

CONNECTION, ROLE = "github-cs-image-system", "cs-image-system-ci"


@pytest.fixture
def world(tmp_path: Path, monkeypatch):
    from cs_image_system.aws_runtime.aws_runtime_builders import AwsCloudBuilder
    from cs_image_system.okta_opa_plugin.okta_opa_tf_group_builder import OktaTfGroupBuilder
    from cs_image_system.okta_opa_plugin.okta_opa_tf_group_models import OktaTfGroupBuilderModel

    run = FixtureRun(tmp_path, monkeypatch)
    ctx = run.ctx
    for gb in ctx.group_builders.values():
        if isinstance(gb, OktaTfGroupBuilder) and isinstance(gb.model, OktaTfGroupBuilderModel):
            object.__setattr__(gb.model, "workload_connection", CONNECTION)
            object.__setattr__(gb.model, "workload_role", ROLE)
    # `test` is launched and durable on the AWS runtime; `test2` is not launched
    ms = ctx.meta_state
    ms.record_launch_params("test", dict(ms.launch_params().get("test") or {}) | {"launched": True, "hostname": "test-001"})
    world: dict = {"power": RUNNING, "registry": [{"id": "s-1", "hostname": "test-001", "address": "10.0.0.1"}],
                   "sft": {}, "calls": []}
    monkeypatch.setattr(AwsCloudBuilder, "can_query_instance_power_state", lambda self: True)
    monkeypatch.setattr(AwsCloudBuilder, "query_instance_power_state", lambda self, n: world["power"])
    monkeypatch.setattr(OktaTfGroupBuilder, "registered_servers", lambda self, group: world["registry"])

    def fake_sft(args, timeout=120, env=None):
        world["calls"].append(list(args))
        world.setdefault("envs", []).append(dict(env or {}))
        return world["sft"].get(args[0], (0, "uid=1001(cs-image-system-ci) gid=1001 groups=1001\ntest-001\n"))
    monkeypatch.setattr(sft_login, "run_sft", fake_sft)   # the client seam is the plugin's
    monkeypatch.setenv("OPA_TOKEN", "opa-token")
    try:
        yield run, world
    finally:
        run.restore_cwd()


def test_an_expired_client_session_is_named_not_silent(world):
    run, w = world
    w["sft"]["resolve"] = (126, "")            # --quiet forbade the browser step (seen live)
    records = lp.login_proof(run.ctx, ["test"], record_only=True)
    resolves = records[0]["checks"][1]
    assert not resolves["ok"] and "sft login" in resolves["detail"] and "OPA_TOKEN" in resolves["detail"]


def test_without_an_opa_token_the_enrolled_client_logs_in_and_the_record_says_so(world, monkeypatch):
    run, _ = world
    monkeypatch.delenv("OPA_TOKEN")
    assert lp.login_proof(run.ctx, ["test"])[0]["as"] == "client"


def test_a_group_without_workload_names_has_nothing_to_prove(world, monkeypatch):
    from cs_image_system.okta_opa_plugin.okta_opa_tf_group_builder import OktaTfGroupBuilder
    run, _ = world
    monkeypatch.setattr(OktaTfGroupBuilder, "can_manage_workload_access", lambda self: False)
    rec = lp.login_proof(run.ctx, ["test"])[0]
    assert rec["skipped"] and "names no workload connection" in rec["checks"][0]["detail"]


def test_workload_facts_come_from_the_builder(world):
    run, _ = world
    from cs_image_system.okta_opa_plugin.workload_token import workload_facts
    facts = workload_facts(run.ctx)
    assert len(facts) == 1 and facts[0]["connection"] == CONNECTION and facts[0]["role"] == ROLE
    assert facts[0]["team"] and facts[0]["api_host"].startswith("https://")


def test_as_the_workload_the_client_is_handed_the_team_and_the_address(world, monkeypatch):
    """The client reads SFT_TEAM and OPA_ADDR from its
    environment for every command; as the workload nothing else sets them."""
    run, w = world
    monkeypatch.delenv("SFT_TEAM", raising=False)
    monkeypatch.delenv("OPA_ADDR", raising=False)
    lp.login_proof(run.ctx, ["test"])
    assert w["calls"][-2][0] == "resolve" and w["calls"][-1][0] == "ssh"
    for env in w["envs"][-2:]:
        assert env["SFT_TEAM"] == "nos-coastal-modeling-cloud-sandbox" and env["OPA_ADDR"].endswith(".pam.okta.com")
    # the environment's own values win, and the enrolled client is left alone
    monkeypatch.setenv("OPA_ADDR", "https://other.example.invalid")
    lp.login_proof(run.ctx, ["test"])
    assert "OPA_ADDR" not in w["envs"][-1] and w["envs"][-1]["SFT_TEAM"]
    monkeypatch.delenv("OPA_TOKEN")
    lp.login_proof(run.ctx, ["test"])
    assert w["envs"][-1] == {}
