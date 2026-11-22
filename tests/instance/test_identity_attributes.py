# SPDX-FileCopyrightText: 2026 Mykel Alvis <mykelalvis@infrastructurebuilder.org>
#
# SPDX-License-Identifier: Apache-2.0

"""The Okta cases of cs-image-system-3's ``tests/test_identity_attributes.py``
(spec 008, T020): the Okta builders' part in identity attributes.

The read-only Okta user builder refuses ``managed: true``; the default of
``managed`` follows the builder type (the read-only builder emits lookups
only); the attributes probe step the Okta group builder's runner carries
names the configuration root and ``--no-dry-run``. Nothing here talks to
Okta or OPA.

History: EXPLORE "User and Group Management", stage 63 low-hanging item 8.
"""
from __future__ import annotations

from pathlib import Path

import yaml
from harness import FixtureRun, copy_config, plain

from cs_image_system.contract.lifecycles import Lifecycle
from cs_image_system.engine import identity_attributes as ia


def _edit(path: Path, fn) -> None:
    data = yaml.safe_load(path.read_text())
    fn(data)
    path.write_text(yaml.safe_dump(data, sort_keys=False))


def overlay(root: Path, *, user_attrs=None, group_attrs=None, managed_user=None, bad=False) -> None:
    def users(d):
        for u in d["users"]:
            if plain(u["name"]) == "avery.alpha":       # the fixture's rosters are encrypted
                if user_attrs is not None:
                    u["attributes"] = user_attrs
                if managed_user is not None:
                    u["managed"] = managed_user
    _edit(root / "groups" / "users.yaml", users)

    def groups(d):
        for g in d["groups"]:
            if g["name"] == "secofs" and group_attrs is not None:
                g["attributes"] = group_attrs
    _edit(root / "groups" / "group-secofs.yaml", groups)


def _run(tmp_path, monkeypatch, **kw) -> FixtureRun:
    root = copy_config(tmp_path)
    overlay(root, **kw)
    return FixtureRun(tmp_path, monkeypatch, config_root=root)


def test_read_only_builder_refuses_managed_true(tmp_path, monkeypatch):
    run = _run(tmp_path, monkeypatch, managed_user=True)
    try:
        errors = ia.validate_identity_items(run.ctx, [Lifecycle.IDENTITY])
        assert len(errors) == 1 and "okta-tf-ro" in errors[0] and "cannot" in errors[0]
    finally:
        run.restore_cwd()


def test_managed_default_follows_the_builder_type(tmp_path, monkeypatch):
    from cs_image_system.okta_opa_plugin.okta_opa_tf_user_builder import OktaTfUserBuilder
    from cs_image_system.okta_opa_plugin.okta_opa_tf_user_ro_builder import OktaTfUserRoBuilder
    assert OktaTfUserBuilder.default_managed() is True
    assert OktaTfUserRoBuilder.default_managed() is False
    run = FixtureRun(tmp_path, monkeypatch)
    try:
        summary = run.run("identity", apply=False)
        assert summary.ok, summary.error
        users_tf = list((run.generated / "identity").rglob("*users*.tf"))
        texts = "\n".join(p.read_text() for p in users_tf)
        assert 'data "okta_user"' in texts and 'resource "okta_user"' not in texts   # RO: lookups only
    finally:
        run.restore_cwd()


def test_the_attributes_probe_step_carries_the_configuration(tmp_path: Path, monkeypatch):
    from cs_image_system.contract.lifecycle import ExecutionLifecyclePhase
    from cs_image_system.okta_opa_plugin.okta_opa_tf_group_builder import OktaTfGroupBuilder
    root = copy_config(tmp_path)
    p = root / "groups" / "group-tcmet.yaml"
    data = yaml.safe_load(p.read_text())
    data["groups"][0]["attributes"] = {"unix_gid": 180999}
    p.write_text(yaml.safe_dump(data, sort_keys=False))
    run = FixtureRun(tmp_path, monkeypatch, config_root=root)
    try:
        gb = next(b for b in run.ctx.group_builders.values() if isinstance(b, OktaTfGroupBuilder))
        deferred = gb.get_commands_to_run_after(ExecutionLifecyclePhase.GROUP_GENERATION).finalize_executables
        lines = [" ".join([str(e.binary or e.name), *[str(a) for a in (e.args or [])]]) for e in deferred]
        probe = [ln for ln in lines if "identity-attributes --probe --dry-run-apply" in ln]
        assert len(probe) == 1, lines
        assert "--root-dir" in probe[0] and "--no-dry-run" in probe[0], probe[0]
    finally:
        run.restore_cwd()
