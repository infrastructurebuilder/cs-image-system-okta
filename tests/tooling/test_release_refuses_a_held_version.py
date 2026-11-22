# SPDX-FileCopyrightText: 2026 Mykel Alvis <mykelalvis@infrastructurebuilder.org>
#
# SPDX-License-Identifier: Apache-2.0

"""A release of the plugin never reuses a version an index has listed for
it (every 0.1.x was released from cs-image-system-3), and never guesses when
the index cannot be asked.
The index is answered by a stand-in; nothing reaches the network."""
from __future__ import annotations

import importlib.machinery
import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "release"


def _release():
    loader = importlib.machinery.SourceFileLoader("okta_release", str(SCRIPT))
    spec = importlib.util.spec_from_loader("okta_release", loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def _index(listed: dict[str, list[str]]):
    def fetch(url: str) -> bytes | None:
        name = url.split("/pypi/")[1].split("/")[0]
        if name not in listed:
            return None                                   # a name the index does not know
        return json.dumps({"releases": {v: [] for v in listed[name]}}).encode()
    return fetch


def test_a_version_the_plugin_ever_held_is_named():
    release = _release()
    fetch = _index({"cs-image-system-okta-opa-plugin": ["0.1.10", "0.1.11", "0.1.12"]})
    for version in ("0.1.10", "0.1.11", "0.1.12"):
        assert release.held(version, "pypi", fetch) == ["cs-image-system-okta-opa-plugin"]


def test_a_version_none_holds_is_free():
    release = _release()
    assert release.held("0.2.0", "test", _index({"cs-image-system-okta-opa-plugin": ["0.1.12"]})) == []
    assert release.held("0.2.0", "pypi", _index({})) == []          # a name the index does not know


def test_an_index_that_cannot_be_asked_refuses_rather_than_guess():
    release = _release()

    def down(url: str) -> bytes | None:
        raise release.Refused("the index could not be asked")
    with pytest.raises(release.Refused):
        release.held("0.2.1", "pypi", down)
