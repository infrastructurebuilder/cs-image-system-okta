# SPDX-FileCopyrightText: 2026 Mykel Alvis <mykelalvis@infrastructurebuilder.org>
#
# SPDX-License-Identifier: Apache-2.0

"""Rewrite the instance suite's golden from a stubbed run of its fixture.

Run on purpose, through ``just golden-regen``, after an intended change to
what the plugin emits; then read the rewritten files one by one.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "instance"))

from harness import FixtureRun  # noqa: E402

from cs_image_system.system import testing as kit  # noqa: E402

GOLDEN = HERE / "instance" / "golden"


def regenerate() -> int:
    mp = pytest.MonkeyPatch()
    try:
        with tempfile.TemporaryDirectory() as td:
            run = FixtureRun(Path(td), mp)
            try:
                summary = run.run("all", apply=True)
                assert summary.ok, summary.error
                out = kit.emitted(run.generated, run.meta_state)
            finally:
                run.restore_cwd()
    finally:
        mp.undo()
    print(f"wrote {kit.write(GOLDEN, out)} golden files under {GOLDEN}")
    return 0


if __name__ == "__main__":
    sys.exit(regenerate())
