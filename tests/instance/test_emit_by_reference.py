# SPDX-FileCopyrightText: 2026 Mykel Alvis <mykelalvis@infrastructurebuilder.org>
#
# SPDX-License-Identifier: Apache-2.0

"""The Okta cases of cs-image-system-3's ``tests/test_emit_by_reference.py``
(spec 008, T020): sensitive values never enter the Okta roots' emission.

The Okta user lookup reads a declared-encrypted email by reference to its
SAME ``ENC[age:...]`` ciphertext and a plain one as a literal; a
declared-encrypted workspace credential reaches the oktapam provider block
by reference, the secret staying environment-side.
"""
from __future__ import annotations

from typing import Any

import pytest
from harness import FIXTURE_CONFIG

from cs_image_system.base.encryption import encrypt_value
from cs_image_system.base.models.user import User
from cs_image_system.hashicorp_utils.collector import TerraformCollector

RECIPIENT = (FIXTURE_CONFIG / ".age-recipient").read_text().strip()


@pytest.fixture(autouse=True)
def _identity(monkeypatch):
    monkeypatch.setenv("CSIS_CONFIG_IDENTITY", str(FIXTURE_CONFIG / ".age-identity"))


def _user(**over: Any) -> User:
    base: dict[str, Any] = dict(name="pat.trip", first_name="Pat", last_name="Trip")
    base.update(over)
    return User(**base)


def test_the_user_lookup_reads_a_declared_email_by_reference_and_a_plain_one_as_a_literal():
    from cs_image_system.okta_opa_plugin.okta_tf_models import OktaTFUser
    col = TerraformCollector()
    marker = encrypt_value("pat.trip@example.org", [RECIPIENT])
    sensitive = lambda key, value: col.sensitive_ref("ws", key, value)   # noqa: E731
    declared = "\n".join(OktaTFUser(_user(email=marker), lookup_depends_on=False, sensitive=sensitive)
                         .generate_terraform_data())
    assert 'value = local.sensitive["email_pat_trip"]' in declared
    assert "pat.trip@example.org" not in declared
    managed = "\n".join(OktaTFUser(_user(email=marker), sensitive=sensitive).generate_terraform())
    assert 'login = local.sensitive["email_pat_trip"]' in managed
    assert 'email = local.sensitive["email_pat_trip"]' in managed
    assert 'first_name = "Pat"' in managed                     # plain stays plain
    assert col.sensitive_values("ws") == {"email_pat_trip": marker}   # one value, both uses
    literal = "\n".join(OktaTFUser(_user(email="pat.trip@example.org"), lookup_depends_on=False,
                                   sensitive=sensitive).generate_terraform_data())
    assert 'value = "pat.trip@example.org"' in literal


def test_a_declared_encrypted_workspace_credential_reaches_the_provider_block_by_reference(monkeypatch):
    from cs_image_system.hashicorp_utils.collector import ConfiguredTerraformProvider
    from cs_image_system.okta_opa_plugin.okta_opa_tf_group_models import OktaTfGroupBuilderModel
    from cs_image_system.okta_opa_plugin.okta_tf_models import OKTATF
    from cs_image_system.okta_opa_plugin.okta_tf_workspace import OKTAPAM_PROVIDER
    monkeypatch.delenv("TF_VAR_team_key", raising=False)
    monkeypatch.setenv("TF_VAR_team_secret", "s")                    # the secret stays environment-side
    key = encrypt_value("real-key", [RECIPIENT])
    ws = OktaTfGroupBuilderModel(type_=OKTATF, name="ws", org="o", team="team", key=key, required_providers=[
        ConfiguredTerraformProvider(name=OKTAPAM_PROVIDER, source="okta/oktapam", version=">= 0.4")])
    ws.finalize()
    col = TerraformCollector()                                        # the run's, handed over by the builder
    cfg = ws.transform_provider(ws.required_providers[0], "ws", col).config
    assert str(cfg["oktapam_key"]) == 'local.sensitive["oktapam_key"]'
    assert str(cfg["oktapam_secret"]) == "var.team_secret"
    assert "real-key" not in "\n".join(col.generate_sensitive_blocks("ws"))
    assert col.sensitive_values("ws") == {"oktapam_key": key}
