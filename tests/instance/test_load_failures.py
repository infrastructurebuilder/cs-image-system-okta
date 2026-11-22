# SPDX-FileCopyrightText: 2026 Mykel Alvis <mykelalvis@infrastructurebuilder.org>
#
# SPDX-License-Identifier: Apache-2.0

"""The Okta case of cs-image-system-3's ``tests/test_load_failures.py``
(spec 008, T020): a missing OPA key pair is the environment's failure (exit
2, one line, no traceback), by the Okta group builder's ``classify_failure``.

history: bundle XII group E (walk findings F10, F30, F41, F42).
"""
from __future__ import annotations

from pathlib import Path

import pytest
from harness import copy_config, stub_environment
from typer.testing import CliRunner

runner = CliRunner()


def _invoke(root: Path, *args: str, catch: bool = False):
    from cs_image_system.system.cli import app
    return runner.invoke(app, ["--root-dir", str(root), *args], catch_exceptions=catch, input="")


@pytest.fixture
def cli_root(tmp_path, monkeypatch):
    stub_environment(monkeypatch)
    return copy_config(tmp_path)


def test_a_missing_opa_key_pair_is_the_environments_failure(cli_root, monkeypatch):
    from cs_image_system.system import cli as gc  # patched where it is read

    def boom(*a, **kw):
        raise ValueError("Okta builder oktagroups is missing a key value.  Expected to find environment variable "
                         "TF_VAR_nos_key for team nos in org acme")
    monkeypatch.setattr(gc, "read_config_and_transform", boom)
    result = _invoke(cli_root, "validate")
    assert result.exit_code == 2, result.output
    assert "TF_VAR_" in result.output and "Traceback" not in result.output
