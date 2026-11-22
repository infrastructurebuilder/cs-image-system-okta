# SPDX-FileCopyrightText: 2026 Mykel Alvis <mykelalvis@infrastructurebuilder.org>
#
# SPDX-License-Identifier: Apache-2.0

"""The Okta cases of cs-image-system-3's ``tests/test_posix_identity.py``
(spec 008, T020): the Okta plugin beside a POSIX identity plugin.

The Okta plugin declares the renderer of the enrollment kind its builder
issues (``sftd-token``) and answers the gid reference the consumers used to
assume. Beside POSIX: the Okta builder's ``posix:`` line is required and
must name a POSIX builder, ``posix: none`` is valid and says what it keeps
off the machines, the read-only builder neither requires nor reads it; an
Okta image bakes the login hook only with a delegate; the Okta accounts
script makes the group with OPA's gid and lists its people in the account
names OPA gives (never derived from a username), stops when a name cannot
be read, and an Okta machine gets its group after apply unless
``posix: none`` or OPA cannot be asked.
"""
from __future__ import annotations

from typing import Any, cast

import pytest

from cs_image_system.contract import enrollment
from cs_image_system.engine import loader


@pytest.fixture
def kinds():
    """The registry as it stands, restored afterwards (the kinds discovery
    registered for the process must survive)."""
    saved = dict(enrollment._KINDS)
    try:
        yield enrollment._KINDS
    finally:
        enrollment._KINDS.clear()
        enrollment._KINDS.update(saved)


def test_the_okta_plugin_declares_the_renderer_of_the_kind_its_builder_issues(kinds):
    from cs_image_system.okta_opa_plugin import okta_opa_tf_group_builder as builder
    from cs_image_system.okta_opa_plugin.main import OktaTypes
    assert builder.SFTD_TOKEN == "sftd-token"
    assert [k.kind for k in OktaTypes().enrollment_kinds] == [builder.SFTD_TOKEN]
    kinds.pop(builder.SFTD_TOKEN, None)
    usable, _ = loader.discover()
    loader.register_declared_kinds(usable)
    assert builder.SFTD_TOKEN in enrollment.registered_kinds()   # the contract's, which the kit re-exports


def test_the_okta_builder_answers_the_gid_reference_the_consumers_used_to_assume():
    from harness import FIXTURE_CONFIG, load_context, stub_environment
    from pytest import MonkeyPatch
    mp = MonkeyPatch()
    stub_environment(mp)
    try:
        ctx = load_context(FIXTURE_CONFIG)
        gb = ctx.group_builders["oktagroups"]
        assert gb.gid_workspace() == "oktagroups"
        assert gb.gid_expression("coops") == 'data.terraform_remote_state.oktagroups.outputs.group_gids["coops"]'
    finally:
        mp.undo()


class _Session:
    """The AWS runtime's power state and session command, faked."""

    def __init__(self, monkeypatch, *, state="running", rc=0, out="posix accounts: in place\n"):
        from cs_image_system.aws_runtime.aws_runtime_builders import AwsCloudBuilder
        self.sent: list[tuple[str, str]] = []
        monkeypatch.setattr(AwsCloudBuilder, "can_query_instance_power_state", lambda s: True)
        monkeypatch.setattr(AwsCloudBuilder, "query_instance_power_state", lambda s, n: state)
        monkeypatch.setattr(AwsCloudBuilder, "run_session_command",
                            lambda s, n, script, timeout=300: self.sent.append((n, script)) or (rc, out))


def _okta_posix(root, value):
    """Set the fixture's oktagroups `posix:` line: a name, `none`, or None (absent)."""
    path = root / "cfg" / "group-builders.yml"
    text = path.read_text()
    old = "    posix: posix-local\n    # key:"
    assert old in text
    path.write_text(text.replace(old, ("" if value is None else f"    posix: {value}\n") + "    # key:"))


def _okta_findings(root, monkeypatch):
    from harness import load_context, stub_environment

    from cs_image_system.engine.commands.validate import check_group_builders
    stub_environment(monkeypatch)
    ctx = load_context(root)
    gb: Any = ctx.group_builders["oktagroups"]      # the Okta builder: posix_delegate is its own
    return [str(e) for e in check_group_builders(ctx)], gb.configuration_notes(), gb


@pytest.mark.parametrize("value,needle", [
    (None, "group builder oktagroups: `posix:` is required -- write `posix: <name>`"),
    ("nosuch", "group builder oktagroups: `posix: nosuch` names no declared group builder"),
    ("okta-groups-ro", "`posix: okta-groups-ro` names a group builder of identity type 'okta'; it must be of type posix"),
])
def test_the_okta_posix_line_is_required_and_must_name_a_posix_builder(tmp_path, monkeypatch, value, needle):
    from harness import copy_config
    root = copy_config(tmp_path)
    _okta_posix(root, value)
    errors, _, _ = _okta_findings(root, monkeypatch)
    assert any(needle in e for e in errors), errors


def test_posix_none_is_valid_and_says_what_it_keeps_off_the_machines(tmp_path, monkeypatch):
    from harness import copy_config
    root = copy_config(tmp_path)
    _okta_posix(root, "none")
    errors, notes, gb = _okta_findings(root, monkeypatch)
    assert errors == [] and gb.posix_delegate() is None
    assert any(n.startswith("group coops:") and "`posix: none`" in n
               for n in notes), notes


def test_the_read_only_okta_builder_neither_requires_nor_reads_posix(monkeypatch):
    from harness import FIXTURE_CONFIG, load_context, stub_environment
    stub_environment(monkeypatch)
    ro: Any = load_context(FIXTURE_CONFIG).group_builders["okta-groups-ro"]
    assert ro.configuration_errors() == [] and ro.configuration_notes() == [] and ro.posix_delegate() is None


def _bake_lines(root, monkeypatch) -> tuple[str, list[str]]:
    """coops' activation and in-bake checks, rendered inside the loaded tree."""
    from harness import load_context, stub_environment
    stub_environment(monkeypatch)
    gb = load_context(root).group_builders["oktagroups"]
    image: Any = type("I", (), {"get_name": lambda self: "img"})()
    coops = next(g for g in gb.get_groups_for_builder() if g.get_name() == "coops")
    return "\n".join(gb.activation_commands(image, coops)), gb.activation_verify_commands(image, coops)


def test_an_okta_image_bakes_the_login_hook_only_with_a_delegate(tmp_path, monkeypatch):
    from harness import copy_config
    bake, checks = _bake_lines(copy_config(tmp_path), monkeypatch)            # the fixture: posix: posix-local
    assert "/usr/local/sbin/csis-group-login" in bake and "pam_exec.so" in bake
    assert "test -x /usr/local/sbin/csis-group-login" in checks
    root = copy_config(tmp_path / "none")
    _okta_posix(root, "none")
    bake, checks = _bake_lines(root, monkeypatch)
    assert "csis-group-login" not in bake and "test -x /usr/local/sbin/csis-group-login" not in checks


class _Opa:
    """OPA's gid lookup and its users' attributes, faked at the builder's
    resolver. Every person's ``unix_user_name`` is their OPA username unless
    ``unix_names`` says otherwise; a name mapped to None has no attribute, and
    ``attribute_error`` makes every read fail."""

    def __init__(self, monkeypatch, gids=None, error=None, unix_names=None, attribute_error=None):
        from cs_image_system.okta_opa_plugin.okta_opa_tf_group_builder import OktaTfGroupBuilder
        self.asked: list[list[str]] = []
        self.attributes_asked: list[str] = []
        gids = {"coops": 180007} if gids is None else gids
        unix_names = dict(unix_names or {})

        def resolve(groups):
            self.asked.append(list(groups))
            if error:
                raise error
            return {g: gids[g] for g in groups if g in gids}

        def user_attributes(name):
            self.attributes_asked.append(name)
            if attribute_error:
                raise attribute_error
            unix = unix_names.get(name, name)
            return {"unix_uid": 150001} | ({"unix_user_name": unix} if unix else {})
        monkeypatch.setattr(OktaTfGroupBuilder, "_resolver", lambda s: type(
            "R", (), {"resolve": staticmethod(resolve), "user_attributes": staticmethod(user_attributes)})())


def test_the_okta_accounts_script_makes_the_group_with_opas_gid_and_lists_its_people(monkeypatch):
    from harness import FIXTURE_CONFIG, load_context, stub_environment
    opa = _Opa(monkeypatch)
    stub_environment(monkeypatch)
    ctx = load_context(FIXTURE_CONFIG)
    gb = ctx.group_builders["oktagroups"]
    coops = next(g for g in gb.get_groups_for_builder() if g.get_name() == "coops")
    script = gb.accounts_script("coops") or ""
    assert opa.asked == [["coops"]]
    assert "groupadd -g 180007 coops" in script and "/etc/csis/groups/coops.members" in script
    assert "useradd" not in script and "# the keys of" not in script     # no keys file: not opted in
    people = {str(m) for m in coops.members} | {str(a) for a in coops.admins} | {str(a) for a in ctx.root_group.admins}
    assert all(p in script for p in people), "members, admins and the root group's admins, as OPA has them"


def _coops_people(ctx, gb) -> list[str]:
    coops = next(g for g in gb.get_groups_for_builder() if g.get_name() == "coops")
    return sorted({str(m) for m in coops.members} | {str(a) for a in coops.admins}
                  | {str(a) for a in ctx.root_group.admins})


def _member_list(script: str, group: str = "coops") -> list[str]:
    """The names the script writes to the group's member list, read from the
    script the way a shell would: the quoted body of its `printf` (the body
    holds a name a line, so the command spans lines)."""
    import re
    import shlex
    found = re.search(rf"^printf '%s' (.*?) > \S*/etc/csis/groups/{group}\.members\.csis", script, re.S | re.M)
    assert found, "the script writes the member list with printf"
    (body,) = shlex.split(found.group(1))
    return [name for name in body.splitlines() if name.strip()]


def test_the_member_list_is_written_in_account_names_read_from_opa(monkeypatch):
    """Found walking the daily driver: the login hook compares the ACCOUNT
    that logs in with the list, name for name, and OPA makes each account
    under the person's `unix_user_name` attribute -- which need not be their
    username. The list carries the attribute's value as OPA gives it."""
    from harness import FIXTURE_CONFIG, load_context, stub_environment
    stub_environment(monkeypatch)
    ctx = load_context(FIXTURE_CONFIG)
    gb = ctx.group_builders["oktagroups"]
    people = _coops_people(ctx, gb)
    assert len(people) >= 2
    odd, plain = people[0], people[1]
    opa = _Opa(monkeypatch, unix_names={odd: "an-account-nothing-like-the-username"})
    listed = _member_list(gb.accounts_script("coops") or "")
    assert sorted(opa.attributes_asked) == people, "every person is asked of OPA, once"
    assert "an-account-nothing-like-the-username" in listed and odd not in listed
    assert plain in listed, "a person whose two names agree is listed as before"
    assert len(listed) == len(people)


@pytest.mark.parametrize("username, account", [("pat.papa", "pat_papa"), ("pat_papa", "pat.papa"),
                                               ("pat.papa", "ppapa"), ("pat.papa", "pat.papa")])
def test_no_account_name_is_ever_derived_from_a_username(monkeypatch, username, account):
    """The operator's ruling: "You cannot depend on translating _ to . and
    vice versa." Whatever the two names look like beside each other, the one
    written is the one OPA answered with, untouched."""
    from cs_image_system.okta_opa_plugin.okta_opa_tf_group_builder import OktaTfGroupBuilder

    class Resolver:
        @staticmethod
        def user_attributes(name):
            return {"unix_user_name": account}
    names = cast(Any, OktaTfGroupBuilder)._account_names(type("B", (), {"name": "b"})(), Resolver(), [username])
    assert names == {username: account}


@pytest.mark.parametrize("opa, needle", [
    ({"attribute_error": RuntimeError("HTTP 503 from OPA")}, "could not be read"),
    ({"unix_names": None}, "carries no unix_user_name"),
])
def test_a_name_opa_does_not_give_stops_the_list_and_guesses_nothing(monkeypatch, opa, needle):
    """A list written without a member would take a standing member OUT of the
    group; a guessed name could let another account in. So the script is not
    made at all, and the error names who."""
    from harness import FIXTURE_CONFIG, load_context, stub_environment
    stub_environment(monkeypatch)
    ctx = load_context(FIXTURE_CONFIG)
    gb = ctx.group_builders["oktagroups"]
    first = _coops_people(ctx, gb)[0]
    kwargs = dict(opa)
    if "unix_names" in kwargs:
        kwargs["unix_names"] = {first: None}
    _Opa(monkeypatch, **kwargs)
    with pytest.raises(ValueError, match=needle) as refused:
        gb.accounts_script("coops")
    assert repr(first) in str(refused.value) and "not rewritten" in str(refused.value)


def test_a_machine_is_left_as_it_stands_when_an_account_name_cannot_be_read(tmp_path, monkeypatch, caplog):
    import logging

    from harness import FixtureRun

    from cs_image_system.contract.lifecycles import Lifecycle
    from cs_image_system.engine import accounts_reconcile
    _Opa(monkeypatch, attribute_error=RuntimeError("HTTP 503 from OPA"))
    session = _Session(monkeypatch)
    run = FixtureRun(tmp_path, monkeypatch)
    try:
        ms = run.ctx.meta_state
        ms.record_launch_params("test", dict(ms.launch_params().get("test") or {"hostname": "test"}) | {"launched": True})
        run.ctx.config["apply_instances"] = True
        with caplog.at_level(logging.ERROR):
            accounts_reconcile.reconcile_accounts(run.ctx, Lifecycle.INSTANCE_IMAGE)
        assert session.sent == [], "nothing is sent to the machine"
        assert "could not be made" in caplog.text and "unix_user_name" in caplog.text
    finally:
        run.restore_cwd()


def test_an_okta_machine_gets_its_group_after_apply(tmp_path, monkeypatch):
    from harness import FixtureRun

    from cs_image_system.contract.lifecycles import Lifecycle
    from cs_image_system.engine import accounts_reconcile
    _Opa(monkeypatch)
    session = _Session(monkeypatch)
    run = FixtureRun(tmp_path, monkeypatch)
    try:
        ms = run.ctx.meta_state
        ms.record_launch_params("test", dict(ms.launch_params().get("test") or {"hostname": "test"}) | {"launched": True})
        run.ctx.config["apply_instances"] = True
        accounts_reconcile.reconcile_accounts(run.ctx, Lifecycle.INSTANCE_IMAGE)
        assert [n for n, _ in session.sent] == ["test"] and "groupadd -g 180007 coops" in session.sent[0][1]
    finally:
        run.restore_cwd()


def test_posix_none_sends_an_okta_machine_nothing(tmp_path, monkeypatch):
    from harness import FixtureRun, copy_config

    from cs_image_system.contract.lifecycles import Lifecycle
    from cs_image_system.engine import accounts_reconcile
    root = copy_config(tmp_path)
    _okta_posix(root, "none")
    session = _Session(monkeypatch)
    run = FixtureRun(tmp_path, monkeypatch, config_root=root)
    try:
        ms = run.ctx.meta_state
        ms.record_launch_params("test", dict(ms.launch_params().get("test") or {"hostname": "test"}) | {"launched": True})
        run.ctx.config["apply_instances"] = True
        accounts_reconcile.reconcile_accounts(run.ctx, Lifecycle.INSTANCE_IMAGE)
        assert session.sent == []
    finally:
        run.restore_cwd()


def test_an_opa_that_cannot_be_asked_is_an_error_not_a_crash(tmp_path, monkeypatch, caplog):
    import logging

    from harness import FixtureRun

    from cs_image_system.contract.lifecycles import Lifecycle
    from cs_image_system.engine import accounts_reconcile
    _Opa(monkeypatch, error=RuntimeError("HTTP 401 from OPA"))
    session = _Session(monkeypatch)
    run = FixtureRun(tmp_path, monkeypatch)
    try:
        ms = run.ctx.meta_state
        ms.record_launch_params("test", dict(ms.launch_params().get("test") or {"hostname": "test"}) | {"launched": True})
        run.ctx.config["apply_instances"] = True
        with caplog.at_level(logging.INFO):
            accounts_reconcile.reconcile_accounts(run.ctx, Lifecycle.INSTANCE_IMAGE)
        assert session.sent == []
        assert any("group coops" in r.getMessage() and "HTTP 401" in r.getMessage()
                   for r in caplog.records if r.levelno >= logging.ERROR)
    finally:
        run.restore_cwd()
