# SPDX-FileCopyrightText: 2026 Mykel Alvis <mykelalvis@infrastructurebuilder.org>
#
# SPDX-License-Identifier: Apache-2.0

"""Pins the Okta plugin's emission for the instance suite's fixture.

A failure here means what the plugin's identity roots, its enrollment or its
activation generate has changed. If the change is intended, run
``just golden-regen`` and read the rewritten files one by one.
"""
from __future__ import annotations

from cs_image_system.system import testing as kit


def test_the_emission_matches_the_suite_golden(okta_run, golden_dir):
    run = okta_run()
    summary = run.run("all", apply=True)
    assert summary.ok, summary.error
    kit.assert_matches(golden_dir, kit.emitted(run.generated, run.meta_state),
                       regenerate_with="just golden-regen")


def test_the_fixture_declares_okta_groups_on_aws_and_nothing_of_another_provider(okta_run):
    """The suite's fixture is an Okta tree on AWS: the identity is Okta's
    (with the POSIX delegate it names), every runtime is the AWS family's."""
    ctx = okta_run().ctx
    assert {type(rb).__module__.split(".")[1] for rb in ctx.runtime_builders.values()} == {"aws_runtime"}
    assert {type(gb).__module__.split(".")[1] for gb in ctx.group_builders.values()} == {
        "okta_opa_plugin", "posix_identity_plugin"}
