# SPDX-FileCopyrightText: 2026 Mykel Alvis <mykelalvis@infrastructurebuilder.org>
#
# SPDX-License-Identifier: Apache-2.0

"""The Okta plugin's instance tests: what needs a whole run.

Each drives a stubbed run over a private copy of the suite's own fixture
(``tests/instance/fixture``) through the published test kit, with the
plugin's own stubs, the AWS stubs its machines run on and the Terraform
roots library's standing in for the outside world (``harness.py``), and the
golden test compares what the run emits with the suite's own golden
(``tests/instance/golden``).
"""
from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path

import aws_stubs
import pytest
from harness import FIXTURE_CONFIG, FIXTURE_TEAM, FixtureRun, copy_config

from cs_image_system.okta_opa_plugin import testing as okta_testing
from cs_image_system.system.testing import isolation
from cs_image_system.tofu_roots import testing as roots_testing

# every instance test finds the root logger as the session started it
root_logger_restored = pytest.fixture(autouse=True)(isolation.root_logger_restored)

INSTANCE = Path(__file__).resolve().parent
FIXTURE = FIXTURE_CONFIG
GOLDEN = INSTANCE / "golden"

#: the stubs a run installs, in order (the harness's ``stub_environment`` binds their arguments)
STUBS = (aws_stubs.stub, okta_testing.credentials, okta_testing.stub, roots_testing.stub)
__all__ = ["FIXTURE", "FIXTURE_TEAM", "GOLDEN", "STUBS"]


@pytest.fixture
def fixture_dir() -> Path:
    """The suite's fixture configuration."""
    return FIXTURE


@pytest.fixture
def golden_dir() -> Path:
    """The suite's golden: the fixture's pinned emission."""
    return GOLDEN


@pytest.fixture
def okta_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Callable[..., FixtureRun]]:
    """A factory for stubbed runs over a private copy of the suite's
    fixture; keyword arguments reach ``FixtureRun``. The working directory
    is restored when the test ends."""
    made: list[FixtureRun] = []

    def make(**kwargs) -> FixtureRun:
        run = FixtureRun(tmp_path, monkeypatch, **kwargs)
        made.append(run)
        return run

    yield make
    for run in made:
        run.restore_cwd()


@pytest.fixture
def okta_root(tmp_path: Path) -> Path:
    """A private copy of the suite's fixture, for a test to edit before it
    loads it."""
    return copy_config(tmp_path)
