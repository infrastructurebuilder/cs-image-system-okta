# SPDX-FileCopyrightText: 2026 Mykel Alvis <mykelalvis@infrastructurebuilder.org>
#
# SPDX-License-Identifier: Apache-2.0

"""Only the system's names come from TestPyPI (cs-image-system-3 specification 013).

Until 1.0 every release of the system goes to TestPyPI alone, so this
workspace's lock takes every name of the system it reaches from there, and
the plugin is tested against the system it will run beside, not PyPI's older one.
TestPyPI also holds stale or foreign copies of common names, so nothing else
may come from it: every third-party name comes from PyPI. The lock is read;
nothing reaches an index.
"""
from __future__ import annotations

import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TESTPYPI = "https://test.pypi.org/simple/"
PYPI = "https://pypi.org/simple"


def _registry_entries() -> list[tuple[str, str]]:
    lock = tomllib.loads((REPO / "uv.lock").read_text())
    return [(p["name"], p["source"]["registry"]) for p in lock["package"] if "registry" in p.get("source", {})]


def test_every_name_of_the_system_in_the_lock_comes_from_testpypi():
    ours = [(n, r) for n, r in _registry_entries() if n.startswith("cs-image-system")]
    assert ours, "the lock takes no name of the system from an index"
    assert all(r == TESTPYPI for _n, r in ours), [x for x in ours if x[1] != TESTPYPI]


def test_no_third_party_name_comes_from_testpypi():
    theirs = [(n, r) for n, r in _registry_entries() if not n.startswith("cs-image-system")]
    assert theirs and all(r.rstrip("/") == PYPI for _n, r in theirs), [x for x in theirs if x[1].rstrip("/") != PYPI]


def test_every_name_of_the_system_has_its_testpypi_source():
    """A name that lost its source would resolve from PyPI at the next lock."""
    doc = tomllib.loads((REPO / "pyproject.toml").read_text())
    sources = doc["tool"]["uv"]["sources"]
    ours = {n for n, _r in _registry_entries() if n.startswith("cs-image-system")}
    assert ours <= {n for n, s in sources.items() if s.get("index") == "testpypi"}
