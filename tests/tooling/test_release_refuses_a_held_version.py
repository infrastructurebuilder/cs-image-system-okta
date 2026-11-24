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


def test_a_version_either_index_ever_held_refuses_the_release(monkeypatch):
    """A version either index ever listed is refused before anything changes
    (PyPI's from before 1.0's decision among them)."""
    release = _release()
    listed = {"pypi": {"cs-image-system-okta-opa-plugin": ["0.1.12"]},
              "test": {"cs-image-system-okta-opa-plugin": ["0.1.12", "0.2.0"]}}
    monkeypatch.setattr(release, "held", lambda version, index, fetch=None: [
        n for n, vs in listed[index].items() if version in vs])
    monkeypatch.setattr(release, "sh", lambda *cmd, **kw: type("Done", (), {"stdout": "0.2.0\n" if "show" in cmd
                                                                            else "", "returncode": 0})())
    monkeypatch.delenv("UV_PUBLISH_TOKEN", raising=False)
    monkeypatch.delenv("PYPI_TOKEN", raising=False)
    with pytest.raises(release.Refused, match="test already lists 0.2.0"):
        release.release("0.2.0", "test", dry=True)


def test_without_a_token_the_dry_form_plans_the_tag_and_no_upload(monkeypatch, capsys):
    release = _release()
    monkeypatch.setattr(release, "held", lambda version, index, fetch=None: [])
    monkeypatch.setattr(release, "sh", lambda *cmd, **kw: type("Done", (), {"stdout": "0.2.0\n" if "show" in cmd
                                                                            else "", "returncode": 0})())
    for name in ("UV_PUBLISH_TOKEN", "PYPI_TOKEN", "TEST_PYPI_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    assert release.release("0.2.0", "test", dry=True) == 0
    said = capsys.readouterr().out
    assert "published by the tag's push" in said and "uv publish" not in said and "tag v0.2.0" in said


def test_pypi_is_refused_naming_the_decision_before_anything_is_asked(monkeypatch, capsys):
    """Until 1.0 a release goes to TestPyPI alone (cs-image-system-3 specification 013)."""
    release = _release()

    def nothing(*a, **kw):
        raise AssertionError("asked or changed something")
    monkeypatch.setattr(release, "held", nothing)
    monkeypatch.setattr(release, "sh", nothing)
    for dry in ("yes", "no"):
        assert release.main(["patch", "pypi", dry]) == 2
        said = capsys.readouterr().out
        assert "PyPI is refused by the standing decision, TestPyPI until 1.0" in said and "nothing was changed" in said
