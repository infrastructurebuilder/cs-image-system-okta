# SPDX-FileCopyrightText: 2026 Mykel Alvis <mykelalvis@infrastructurebuilder.org>
#
# SPDX-License-Identifier: Apache-2.0

"""The Okta case of cs-image-system-3's ``tests/test_provider_aliases.py``
(spec 008, T020): the server aliases written for sftd.

The script is the identity plugin's (its agent, its file): it rewrites the
last ``AltNames:`` block of sftd's configuration and restarts sftd only on
a change; the core asks the group builder for it and reads only the two
closing words.
"""
from __future__ import annotations

import pytest


def test_the_script_rewrites_the_last_block_and_restarts_only_on_change():
    """The script is the identity plugin's (its agent, its file); the core
    asks the group builder for it and reads only the two closing words."""
    from cs_image_system.okta_opa_plugin.okta_opa_tf_group_builder import OktaTfGroupBuilder
    from cs_image_system.okta_opa_plugin.server_aliases import alt_names_script
    assert OktaTfGroupBuilder.alias_registration_script(None, ["a-b"]) == alt_names_script(["a-b"])  # type: ignore[arg-type]
    s = alt_names_script(["ip-10-26-34-156"])
    assert "AltNames:" in s and "  - ip-10-26-34-156" in s
    assert "sed -i '/^AltNames:/,$d'" in s          # replace from the heading to EOF
    assert "ALTNAMES_UNCHANGED; exit 0" in s          # idempotent path first
    assert "systemctl restart sftd" in s and s.index("UNCHANGED") < s.index("restart sftd")
    assert "tee -a" in s and "| sudo tee " not in s.replace("tee -a", "")   # append, never truncate
    assert 'want=""' in alt_names_script([])       # no aliases: the block is removed
    with pytest.raises(ValueError, match="not a hostname label"):
        alt_names_script(["ip 10"])
