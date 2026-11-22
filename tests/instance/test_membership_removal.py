# SPDX-FileCopyrightText: 2026 Mykel Alvis <mykelalvis@infrastructurebuilder.org>
#
# SPDX-License-Identifier: Apache-2.0

"""The Okta cases of cs-image-system-3's ``tests/test_membership_removal.py``
(spec 008, T020): a membership the YAML dropped is removed by the run.

The identity runner's prune step lists the state it is bound to and knows
which attachments the declaration dropped. It names the ones the plan will
destroy in a file beside the plan, and the gate reads that file: each entry
sanctions the one address it spells. Every run rewrites the list; an OPA
that cannot say leaves the removal to the plan and sanctions it; a root
with no state or a failed listing sanctions nothing; only the managed OPA
group root's gate reads the list.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from harness import FixtureRun
from test_stale_attachments import _addr, _fake_tofu, _group_builder, _Opa, _root

from cs_image_system.contract.names import super_safe_name
from cs_image_system.engine.commands.gate import sanctioned_addresses
from cs_image_system.okta_opa_plugin import okta_opa_tf_group_builder as gbmod

FILE = gbmod.OktaTfGroupBuilder.SANCTIONED_REMOVALS


@pytest.fixture
def run(tmp_path: Path, monkeypatch):
    r = FixtureRun(tmp_path, monkeypatch)
    try:
        yield r
    finally:
        r.restore_cwd()


def test_a_dropped_membership_opa_still_holds_is_sanctioned_and_nothing_else_is(run, monkeypatch, caplog):
    ctx = run.ctx
    gb = _group_builder(ctx)
    g = gb.get_groups_for_builder()[0]
    name, label = g.get_name(), super_safe_name(g.name)
    declared_member = sorted(str(m) for m in g.members)[0]
    root_admin = sorted(str(a) for a in ctx.root_group.admins)[0]
    tofu, journal = _fake_tofu(run.config_root, [
        f"module.group_{label}.oktapam_group.user",
        _addr(label, "members", declared_member),          # still declared
        _addr(label, "admins", root_admin),                # still declared (the root group's admin)
        _addr(label, "members", "held.member"),            # dropped, OPA holds it: the run removes it
        _addr(label, "admins", "held.admin"),              # the same, of the admins' group
        _addr(label, "members", "gone.member"),            # dropped, OPA lacks it: leaves state, no destroy to allow
        _addr("nosuchgroup", "members", "x"),              # not a managed group of this builder
    ])
    opa = _Opa({f"{name}_user": ["held.member", declared_member], f"{name}_admin": ["held.admin", root_admin]})
    monkeypatch.setattr(gbmod.OktaTfGroupBuilder, "_resolver", lambda self: opa)
    cwd = _root(run.config_root)
    with caplog.at_level("INFO"):
        assert gb.prune_stale_attachments(tofu, "r1", cwd) == 0
    assert sanctioned_addresses(cwd / FILE) == [_addr(label, "members", "held.member"), _addr(label, "admins", "held.admin")]
    assert journal.read_text().splitlines() == [_addr(label, "members", "gone.member")]
    said = [r.message for r in caplog.records if "'held.member'" in r.message]
    assert said and "the gate allows" in said[0]


def test_every_run_rewrites_the_list_so_an_earlier_one_sanctions_nothing(run, monkeypatch):
    gb = _group_builder(run.ctx)
    g = gb.get_groups_for_builder()[0]
    label = super_safe_name(g.name)
    cwd = _root(run.config_root)
    (cwd / FILE).write_text(_addr(label, "members", "from.an.earlier.run") + "\n")
    monkeypatch.setattr(gbmod.OktaTfGroupBuilder, "_resolver", lambda self: _Opa({}))
    tofu, _ = _fake_tofu(run.config_root, [_addr(label, "members", sorted(str(m) for m in g.members)[0])])
    assert gb.prune_stale_attachments(tofu, "r2", cwd) == 0
    assert (cwd / FILE).is_file() and sanctioned_addresses(cwd / FILE) == []


@pytest.mark.parametrize("opa", ["silent", "no-credentials"])
def test_an_opa_that_cannot_say_leaves_the_removal_to_the_plan_and_sanctions_it(run, monkeypatch, opa):
    """The declaration is what asks for the removal; OPA is asked only so that
    a membership already gone can leave state without an error. When OPA
    cannot say, the plan shows the destroy and it is still the declaration's."""
    gb = _group_builder(run.ctx)
    g = gb.get_groups_for_builder()[0]
    label = super_safe_name(g.name)
    cwd = _root(run.config_root)
    tofu, journal = _fake_tofu(run.config_root, [_addr(label, "members", "dropped.member")])
    if opa == "silent":
        monkeypatch.setattr(gbmod.OktaTfGroupBuilder, "_resolver", lambda self: _Opa({}))
    else:
        def no_creds(self):
            raise ValueError("OPA credentials for team 'x' not found in the environment")
        monkeypatch.setattr(gbmod.OktaTfGroupBuilder, "_resolver", no_creds)
    assert gb.prune_stale_attachments(tofu, "r1", cwd) == 0
    assert not journal.exists(), "nothing leaves state on a guess"
    assert sanctioned_addresses(cwd / FILE) == [_addr(label, "members", "dropped.member")]


def test_a_root_with_no_state_or_a_failed_listing_sanctions_nothing(run, tmp_path):
    gb = _group_builder(run.ctx)
    for said, code in (("Error: No state file was found!", 0), ("Backend initialization required", 1)):
        cwd = tmp_path / f"root-{code}"
        cwd.mkdir()
        (cwd / FILE).write_text("module.group_x.oktapam_user_group_attachment.members[\"stale\"]\n")
        tofu = cwd / "tofu"
        tofu.write_text(f"#!/bin/sh\necho '{said}' >&2\nexit 1\n")
        tofu.chmod(0o755)
        assert gb.prune_stale_attachments(str(tofu), "r1", cwd) == code
        assert sanctioned_addresses(cwd / FILE) == []


def test_only_the_identity_roots_gate_reads_the_list(run):
    assert run.run("all", apply=False).ok
    gates = {}
    for script in sorted(run.generated.glob("*/run-*.sh")):
        gates[script.parent.name] = [ln for ln in script.read_text().splitlines() if "gate-plan" in ln]
    assert gates["identity"], "the identity lifecycle has a gated root"
    okta = [ln for ln in gates["identity"] if "oktagroups" in ln]
    assert okta and all(f"--allow-destroy-from {FILE}" in ln for ln in okta)
    for lifecycle, lines in gates.items():
        for ln in lines:
            if "oktagroups" not in ln:
                assert "--allow-destroy-from" not in ln, f"{lifecycle}: only the managed OPA group root has removals to sanction"
