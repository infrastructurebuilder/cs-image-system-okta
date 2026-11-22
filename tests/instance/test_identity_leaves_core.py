# SPDX-FileCopyrightText: 2026 Mykel Alvis <mykelalvis@infrastructurebuilder.org>
#
# SPDX-License-Identifier: Apache-2.0

"""The Okta cases of cs-image-system-3's ``tests/test_identity_leaves_core.py``
(spec 008, T020): what the Okta plugin brings to the system through the
contract.

The installed CLI carries the plugin's commands (``workload``, ``verify
login``) from its real entry point; a tree with Okta profile fields loads
with the plugin's injected user model and is refused without it; the core's
user carries none of those fields; the state query's words for workload
access are the plugin's.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
from harness import copy_config, load_context, stub_environment
from typer.testing import CliRunner

from cs_image_system.contract.constants import VCT

runner = CliRunner()


def test_the_installed_cli_carries_the_okta_commands_from_the_real_entry_point(monkeypatch):
    """The console script read the installed entry point at import: the two
    commands answer `--help` without a tree (the root callback reads the
    help request off the process arguments, which the runner sets here)."""
    import sys

    from typer.main import get_command

    from cs_image_system.engine.commands.login_proof import verify_login_command
    from cs_image_system.system.cli import app
    assert "workload" in {g.name for g in app.registered_groups}
    assert [c.callback for g in app.registered_groups if g.name == "verify" and g.typer_instance
            for c in g.typer_instance.registered_commands if c.name == "login"] == [verify_login_command]
    root = get_command(app)
    verify = root.commands["verify"]  # type: ignore[attr-defined]
    assert "login" in verify.commands and "workload" in root.commands  # type: ignore[attr-defined]
    for args in (["workload", "--help"], ["verify", "login", "--help"], ["workload", "token", "--help"]):
        monkeypatch.setattr(sys, "argv", ["cs-image-system", *args])
        result = runner.invoke(app, args)
        assert result.exit_code == 0, result.output
        assert "Usage: " in result.output


def _with_a_profile_field(root: Path) -> None:
    path = root / "groups" / "users.yaml"
    text = path.read_text()
    old = "    last_name: Alpha\n"
    assert old in text
    path.write_text(text.replace(old, old + '    mobile_phone: "+1-555-0100"\n    department: Modeling\n', 1))


def test_a_tree_with_okta_profile_fields_loads_with_the_plugin_and_is_refused_without_it(tmp_path, monkeypatch):
    from cs_image_system.base.models.user import User
    from cs_image_system.engine.config_loader import read_config_and_transform
    from cs_image_system.engine.loader import installed_registry
    from cs_image_system.okta_opa_plugin.okta_user import OktaUser
    stub_environment(monkeypatch)
    root = copy_config(tmp_path)
    _with_a_profile_field(root)
    ctx = load_context(root)
    avery = next(u for u in ctx.users if u.first_name == "Avery")
    assert isinstance(avery, OktaUser) and isinstance(avery, User)
    assert avery.mobile_phone == "+1-555-0100" and avery.department == "Modeling"
    assert avery.get_display_name() == avery.name, "the base display name survives the profile field of that name"
    assert avery.get_self_injected_name() == "user", "templates say {{ user.name }} whatever the subclass"
    assert "{{" not in str(avery.email) and str(avery.email).startswith(avery.name)
    others = [u for u in ctx.users if u is not avery]
    assert others and all(isinstance(u, OktaUser) and u.mobile_phone is None for u in others)
    # the plugin's emitter reads the fields from the subclass
    from cs_image_system.okta_opa_plugin.okta_tf_models import OktaTFUser
    hcl = "\n".join(OktaTFUser(avery, provider="okta.x").generate_terraform())
    assert 'mobile_phone = "+1-555-0100"' in hcl and 'department = "Modeling"' in hcl
    # without the plugin's injected model, the core's User is the item model and the keys are unknown
    reg = installed_registry()           # the plugins loaded into a registry of the test's own; the run below loads into it
    for key in reg.registration_keys(VCT.USER_MODEL):
        del reg.models[key]
    reg.defaults_registry.pop(VCT.USER_MODEL, None)
    with pytest.raises(Exception, match="mobile_phone|department|[Ee]xtra"):
        read_config_and_transform(cast(Any, SimpleNamespace(obj={})), root, False, dry_run=True, overlays=[],
                                  undeclare=[], reg=reg)


def test_the_core_user_carries_no_profile_field():
    import dataclasses

    from cs_image_system.base.models.user import User
    from cs_image_system.okta_opa_plugin.okta_user import OKTA_PROFILE_FIELDS
    names = {f.name for f in dataclasses.fields(User)}
    assert not names & set(OKTA_PROFILE_FIELDS), names & set(OKTA_PROFILE_FIELDS)
    assert {"name", "first_name", "last_name", "middle_name", "email", "description", "is_service_account",
            "is_enabled", "managed", "attributes", "uid", "public_keys"} <= names
    assert not hasattr(User, "as_profile")


def test_the_state_query_words_for_workload_access_are_the_plugins(tmp_path, monkeypatch):
    from cs_image_system.contract.group import WORKLOAD_CONNECTION_INACTIVE, WORKLOAD_ROLE_ABSENT
    from cs_image_system.engine import state_query as sq
    from cs_image_system.okta_opa_plugin.okta_opa_tf_group_builder import OktaTfGroupBuilder
    stub_environment(monkeypatch)
    ctx = load_context(copy_config(tmp_path))
    gb = next(b for b in ctx.group_builders.values() if isinstance(b, OktaTfGroupBuilder))
    expected = {"role": "ci-role", "policy": "g_v1_security_policy_ci", "mirrors": "g_v1_security_policy_user"}
    real = {"role": {"present": False}, "policy": {"present": False}}
    [drift] = sq.workload_drift("g", expected, real, gb)
    assert "CI_SETUP.md section 3.5" in drift.detail and "OPA" in drift.detail
    [plain] = sq.workload_drift("g", expected, real)                     # no builder: the core's words
    assert "OPA" not in plain.detail and "ci-role" in plain.detail
    assert "DRAFT" in gb.workload_access_detail(WORKLOAD_CONNECTION_INACTIVE, expected, real)
    assert "OPA" in gb.workload_access_detail(WORKLOAD_ROLE_ABSENT, expected, real)
