# SPDX-FileCopyrightText: 2026 Mykel Alvis <mykelalvis@infrastructurebuilder.org>
#
# SPDX-License-Identifier: Apache-2.0

"""The Okta cases of cs-image-system-3's ``tests/test_release_whole.py``
(spec 008, T020): the workload token.

``cs-image-system workload token`` mints an OPA token from the job's GitHub
OIDC token: it prints the token alone and masks both on stderr, hands the
client the address and the team in its environment, fills missing names
from the configuration, and refuses outside a job or on a refused token.
``test_workload_probe.py`` imports ``_job_env`` and ``_stub_minting`` from
here.
"""
from __future__ import annotations

import os

from typer.testing import CliRunner

from cs_image_system.system.cli import app

# -------------------------------------------------------- workload token

def _stub_minting(monkeypatch, *, rc=0, token="opa-token-value", verdict="ok\n"):
    from cs_image_system.okta_opa_plugin import workload_token as wt
    jwt = "hdr." + __import__("base64").urlsafe_b64encode(
        b'{"iss":"https://token.actions.githubusercontent.com","repository":"o/r","sub":"repo:o/r:ref:refs/heads/main"}').decode().rstrip("=") + ".sig"
    monkeypatch.setattr(wt, "fetch_oidc_token", lambda url, bearer: jwt)
    calls: list = []
    def authenticate(names, presented):
        calls.append((names, presented))
        return rc, token, verdict
    monkeypatch.setattr(wt, "sft_workload_authenticate", authenticate)
    return jwt, calls


def _job_env(monkeypatch, **names):
    monkeypatch.setenv("ACTIONS_ID_TOKEN_REQUEST_URL", "https://runner.invalid/token")
    monkeypatch.setenv("ACTIONS_ID_TOKEN_REQUEST_TOKEN", "bearer-value")
    for k, v in names.items():
        monkeypatch.setenv(k, v)


def test_workload_token_prints_the_token_alone_and_masks_both_on_stderr(monkeypatch):
    jwt, calls = _stub_minting(monkeypatch)
    _job_env(monkeypatch, OPA_WORKLOAD_CONNECTION="conn", OPA_WORKLOAD_ROLE="role", SFT_TEAM="team",
             OPA_ADDR="https://x.pam.okta.com")
    monkeypatch.delenv("CSIS_CONFIG_IDENTITY", raising=False)
    from cs_image_system.okta_opa_plugin.workload_token import WorkloadNames, mint_token
    said: list[str] = []
    token = mint_token(WorkloadNames("conn", "role", "team", "https://x.pam.okta.com"), dict(os.environ),
                       say=said.append, fetch=lambda u, b: jwt,
                       authenticate=lambda n, j: (0, "opa-token-value\n", "verdict line\n"))
    assert token == "opa-token-value"
    assert said[0] == f"::add-mask::{jwt}" and "::add-mask::opa-token-value" in said
    assert any(ln == "claim repository: o/r" for ln in said) and "verdict line" in said
    # the command: the token is the ONLY thing on stdout, from a checkout with no configuration
    result = CliRunner().invoke(app, ["--root-dir", "/nowhere", "workload", "token"])
    assert result.exit_code == 0, result.output
    assert result.stdout == "opa-token-value"
    assert calls and calls[0][0].connection == "conn" and calls[0][1] == jwt
    assert "::add-mask::" in result.stderr and "opa-token-value" not in result.stdout.replace("opa-token-value", "", 1)


def test_the_client_is_handed_the_address_and_the_team_in_its_environment(monkeypatch):
    """`sft workload authenticate` reads OPA_ADDR (and the
    team) from its environment; the first performing run from the reference
    configuration failed with `environment variable OPA_ADDR is not set`."""
    from cs_image_system.okta_opa_plugin import workload_token as wt
    seen: dict = {}

    class _Proc:
        returncode, stdout, stderr = 0, "tok\n", ""

    def fake_run(cmd, **kw):
        seen["cmd"] = cmd
        seen["env"] = kw["env"]
        return _Proc()
    monkeypatch.setattr(wt.subprocess, "run", fake_run)
    monkeypatch.delenv("OPA_ADDR", raising=False)
    monkeypatch.delenv("SFT_TEAM", raising=False)
    rc, out, _ = wt.sft_workload_authenticate(wt.WorkloadNames("conn", "role", "team", "https://x.pam.okta.com"), "jwt")
    assert rc == 0 and out == "tok\n"
    assert seen["env"]["OPA_ADDR"] == "https://x.pam.okta.com" and seen["env"]["SFT_TEAM"] == "team"
    assert seen["env"]["GH_OIDC_JWT"] == "jwt" and "--team" in seen["cmd"] and "--role-hint" in seen["cmd"]


def test_workload_token_fills_missing_names_from_the_configuration(monkeypatch, tmp_path):
    from harness import copy_config, stub_environment
    stub_environment(monkeypatch)
    root = copy_config(tmp_path)
    # the fixture's builder names no workload objects; this copy's does
    gb = root / "cfg" / "group-builders.yml"
    gb.write_text(gb.read_text().replace('    team: "nos-coastal-modeling-cloud-sandbox"\n',
                                         '    team: "nos-coastal-modeling-cloud-sandbox"\n'
                                         '    workload_connection: github-cs-image-system\n'
                                         '    workload_role: cs-image-system-ci\n', 1))
    jwt, calls = _stub_minting(monkeypatch)
    _job_env(monkeypatch)
    for v in ("OPA_WORKLOAD_CONNECTION", "OPA_WORKLOAD_ROLE", "SFT_TEAM", "OPA_ADDR"):
        monkeypatch.delenv(v, raising=False)
    result = CliRunner().invoke(app, ["--root-dir", str(root), "workload", "token"])
    assert result.exit_code == 0, result.output
    names = calls[0][0]
    assert names.team == "nos-coastal-modeling-cloud-sandbox" and names.connection == "github-cs-image-system"
    assert names.role == "cs-image-system-ci" and "pam.okta.com" in names.api_host
    assert result.stdout == "opa-token-value"


def test_workload_token_refuses_outside_a_job_and_reports_a_refused_token(monkeypatch):
    for v in ("ACTIONS_ID_TOKEN_REQUEST_URL", "ACTIONS_ID_TOKEN_REQUEST_TOKEN"):
        monkeypatch.delenv(v, raising=False)
    _stub_minting(monkeypatch)
    monkeypatch.setenv("OPA_WORKLOAD_CONNECTION", "c"); monkeypatch.setenv("OPA_WORKLOAD_ROLE", "r")
    monkeypatch.setenv("SFT_TEAM", "t"); monkeypatch.setenv("OPA_ADDR", "https://x")
    result = CliRunner().invoke(app, ["workload", "token"])
    assert result.exit_code == 2 and "not a GitHub Actions job" in result.output
    _stub_minting(monkeypatch, rc=1, token="", verdict="the connection is a draft\n")
    _job_env(monkeypatch)
    result = CliRunner().invoke(app, ["workload", "token"])
    assert result.exit_code == 1 and result.stdout == "" and "exited 1" in result.stderr and "the connection is a draft" in result.stderr
    _stub_minting(monkeypatch, rc=0, token="", verdict="")
    result = CliRunner().invoke(app, ["workload", "token"])
    assert result.exit_code == 1 and "issued no token" in result.stderr

