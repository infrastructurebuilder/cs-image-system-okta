# SPDX-FileCopyrightText: 2026 Mykel Alvis <mykelalvis@infrastructurebuilder.org>
#
# SPDX-License-Identifier: Apache-2.0

"""A configuration names the plugin's words bare or qualified, as before the
move: the distribution keeps its name, so the namespace derived from it
(``okta-opa``, as cs-image-system-3's tests/test_registration_namespaces.py
names it) stays, and a tree written against the plugin in cs-image-system-3
loads unchanged (spec 008, story 3, scenario 2)."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from harness import FixtureRun, copy_config

#: (file under cfg/, list key, builder name, its qualified type)
QUALIFIED = (
    ("group-builders.yml", "group_builders", "oktagroups", "okta-opa/okta-tf"),
    ("group-builders.yml", "group_builders", "okta-groups-ro", "okta-opa/okta-tf-ro"),
    ("group-builders.yml", "user_builders", "okta-tf-users", "okta-opa/okta-tf-ro"),
)


def _qualify(root: Path) -> None:
    for name, key, builder, word in QUALIFIED:
        path = root / "cfg" / name
        data = yaml.safe_load(path.read_text())
        entry = next(e for e in data[key] if e["name"] == builder)
        entry["type"] = word
        path.write_text(yaml.safe_dump(data, sort_keys=False))


@pytest.mark.parametrize("qualified", [False, True], ids=["bare", "qualified"])
def test_the_plugin_words_load_bare_and_qualified(tmp_path: Path, monkeypatch, qualified: bool):
    root = copy_config(tmp_path)
    if qualified:
        _qualify(root)
    run = FixtureRun(tmp_path, monkeypatch, config_root=root)
    try:
        ctx = run.ctx
        for name in ("oktagroups", "okta-groups-ro"):
            assert type(ctx.group_builders[name]).__module__.startswith("cs_image_system.okta_opa_plugin"), name
        assert type(ctx.user_builders["okta-tf-users"]).__module__.startswith("cs_image_system.okta_opa_plugin")
    finally:
        run.restore_cwd()
