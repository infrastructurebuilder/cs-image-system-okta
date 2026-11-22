# SPDX-FileCopyrightText: 2026 Mykel Alvis <mykelalvis@infrastructurebuilder.org>
#
# SPDX-License-Identifier: Apache-2.0

"""The Okta cases of cs-image-system-3's ``tests/test_state_query_verdicts.py``
(spec 008, T020): how the Okta group builder's answer becomes a verdict.

The builder's real `query_state` tells a 404 (a real absence) from a call
that failed (an error the query reports as unavailable), and attaches a
group's OPA module objects from the resource-group and policy listings,
omitting them when OPA is silent.

history: bundle V item 1, XII items 9, 13 and 33, XIV item 6.
"""
from __future__ import annotations

import urllib.error
from email.message import Message
from pathlib import Path

import pytest
from harness import FixtureRun

from cs_image_system.engine import state_query as sq
from cs_image_system.okta_opa_plugin import okta_opa_tf_group_builder as gbmod
from cs_image_system.okta_opa_plugin.opa_gids import GID_ATTRIBUTE

# captured at import, before the harness's stub replaces it on the class
_REAL_QUERY_STATE = gbmod.OktaTfGroupBuilder.query_state


@pytest.fixture
def run(tmp_path: Path, monkeypatch):
    r = FixtureRun(tmp_path, monkeypatch)
    try:
        yield r
    finally:
        r.restore_cwd()


def _group_builder(ctx) -> gbmod.OktaTfGroupBuilder:
    return next(b for b in ctx.group_builders.values() if isinstance(b, gbmod.OktaTfGroupBuilder))


def _http(code: int, reason: str) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("https://opa.invalid", code, reason, Message(), None)


def test_the_builder_tells_a_404_from_a_call_that_failed(run, monkeypatch):
    gb = _group_builder(run.ctx)
    names = [g.get_name() for g in gb.get_groups_for_builder()]
    assert len(names) >= 3
    monkeypatch.setattr(gbmod, "credentials_from_env", lambda team: ("k", "s"))
    monkeypatch.setattr(gbmod.OktaTfGroupBuilder, "can_manage_workload_access", lambda self: False)
    monkeypatch.setattr(gbmod.OpaGidResolver, "group_users", lambda self, g: None)
    monkeypatch.setattr(gbmod.OpaGidResolver, "project_enrollment_tokens", lambda self, g: None)
    monkeypatch.setattr(gbmod.OpaGidResolver, "security_policies", lambda self: None)   # silent, never asked
    monkeypatch.setattr(gbmod.OpaGidResolver, "resource_groups", lambda self: None)

    def attributes(self, server_group):
        if server_group == f"{names[0]}{gbmod.USER_GROUP_SUFFIX}":
            raise _http(404, "Not Found")
        if server_group == f"{names[1]}{gbmod.USER_GROUP_SUFFIX}":
            raise _http(401, "Unauthorized")
        if server_group == f"{names[2]}{gbmod.USER_GROUP_SUFFIX}":
            raise OSError("Connection refused")
        return {GID_ATTRIBUTE: 180000, gbmod.GROUP_NAME_ATTRIBUTE: server_group}
    monkeypatch.setattr(gbmod.OpaGidResolver, "group_attributes", attributes)
    # the harness stubs query_state on the class (every group present, gid 1); this test is about the real one
    recs = _REAL_QUERY_STATE(gb)
    assert recs[names[0]] == {"present": False}, "OPA answered: the group is not there"
    assert recs[names[1]] == {"present": False, "error": "HTTP 401 Unauthorized"}
    assert recs[names[2]]["present"] is False and "Connection refused" in recs[names[2]]["error"]
    for other in names[3:]:
        assert recs[other]["present"] is True and "error" not in recs[other]


def _opa(monkeypatch, *, policies, rgs, detail):
    monkeypatch.setattr(gbmod, "credentials_from_env", lambda team: ("k", "s"))
    monkeypatch.setattr(gbmod.OktaTfGroupBuilder, "can_manage_workload_access", lambda self: False)
    monkeypatch.setattr(gbmod.OpaGidResolver, "group_users", lambda self, g: None)
    monkeypatch.setattr(gbmod.OpaGidResolver, "project_enrollment_tokens", lambda self, g: None)
    monkeypatch.setattr(gbmod.OpaGidResolver, "group_attributes",
                        lambda self, g: {GID_ATTRIBUTE: 180000, gbmod.GROUP_NAME_ATTRIBUTE: g})
    monkeypatch.setattr(gbmod.OpaGidResolver, "security_policies", lambda self: policies)
    monkeypatch.setattr(gbmod.OpaGidResolver, "resource_groups", lambda self: rgs)
    monkeypatch.setattr(gbmod.OpaGidResolver, "resource_group", lambda self, rg_id: detail(rg_id))


def test_the_builder_attaches_the_module_objects_and_omits_them_when_opa_is_silent(run, monkeypatch):
    gb = _group_builder(run.ctx)
    name = gb.get_groups_for_builder()[0].get_name()
    rg = {"id": "rg-1", "name": f"{name}_rg", "description": f"Resource group for Okta group {name}",
          "delegated_resource_admin_groups": [{"id": "x", "name": "someone_else_admin"}]}
    _opa(monkeypatch, policies=[], rgs=[{"id": "rg-1", "name": f"{name}_rg"}], detail=lambda rg_id: rg)
    objects = _REAL_QUERY_STATE(gb)[name]["module_objects"]
    assert objects["resource_group"]["diff"] == [f"delegated_admins: ['someone_else_admin'] != ['{name}_admin']"]
    assert objects["user_policy"] == {"name": f"{name}_v1_security_policy_user", "present": False}
    drift = sq.module_drift(name, objects)
    assert {d.drift for d in drift} == {sq.DRIFT_CHANGED, sq.DRIFT_MISSING}
    # OPA silent on either listing, or on the group's own record: nothing is said, nothing guessed
    _opa(monkeypatch, policies=None, rgs=[], detail=lambda rg_id: rg)
    assert "module_objects" not in _REAL_QUERY_STATE(gb)[name]
    _opa(monkeypatch, policies=[], rgs=[{"id": "rg-1", "name": f"{name}_rg"}], detail=lambda rg_id: None)
    assert "module_objects" not in _REAL_QUERY_STATE(gb)[name]
