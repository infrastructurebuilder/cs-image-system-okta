# SPDX-FileCopyrightText: 2026 Mykel Alvis <mykelalvis@infrastructurebuilder.org>
#
# SPDX-License-Identifier: Apache-2.0

"""The Okta case of cs-image-system-3's ``tests/test_bootstrap_coverage.py``
(spec 008, T020): the Okta bootstrap section audits what it never makes
(the OPA workload connection, the OPA service user and its key pair are
BY HAND), every row with a reason.

history: bundle XII items 5 and 33, XX items 1 to 3.
"""
from __future__ import annotations


def test_the_okta_section_audits_what_it_never_makes():
    from cs_image_system.okta_opa_plugin.bootstrap import render
    rendered = render({"workload_connection": "github-widgets", "workload_role": "widgets-ci", "team": "acme",
                       "api_host": "acme.pam.okta.com", "production_branch": "main", "connection_exists": True,
                       "connection_active": False, "connection_requires_repository": True, "role_exists": False,
                       "role_bound": False, "role_pinned": False, "builder_names_them": False, "okta_app_authenticates": True,
                       "okta_app_read_only": True, "okta_app_readable": False})
    statuses = {res: status for res, status, _ in rendered.coverage}
    assert statuses["the OPA workload connection `github-widgets`"] == "BY HAND"
    assert statuses["the OPA service user and its key pair"] == "BY HAND"
    assert all(why for _, _, why in rendered.coverage)
