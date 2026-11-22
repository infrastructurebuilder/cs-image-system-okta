# SPDX-FileCopyrightText: 2026 Mykel Alvis <mykelalvis@infrastructurebuilder.org>
#
# SPDX-License-Identifier: Apache-2.0

"""The Okta case of cs-image-system-3's ``tests/test_os_types.py`` (spec
008, T020): the OS type owns the package manager, and OktaPAM publishes
deb and rpm repositories and nothing for alpine, so the Okta group builder
refuses an alpine image rather than guessing another family's lines.
"""
from __future__ import annotations

import pytest
from harness import FixtureRun


@pytest.fixture
def fixture_run(tmp_path, monkeypatch):
    run = FixtureRun(tmp_path, monkeypatch)
    yield run
    run.restore_cwd()


def test_okta_refuses_an_alpine_image_rather_than_guessing(fixture_run):
    """OktaPAM publishes deb and rpm repositories and nothing for alpine:
    the identity plugin says so instead of emitting another family's lines."""
    okta = fixture_run.ctx.group_builders["oktagroups"]
    with pytest.raises(ValueError, match="publishes no apk package"):
        okta.base_image_prerequisites("alpine")
