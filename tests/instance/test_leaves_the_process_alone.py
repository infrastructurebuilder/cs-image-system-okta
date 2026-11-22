# SPDX-FileCopyrightText: 2026 Mykel Alvis <mykelalvis@infrastructurebuilder.org>
#
# SPDX-License-Identifier: Apache-2.0

"""Loading the Okta plugin and running it changes nothing process-wide.

A load and a whole stubbed run of the suite's fixture are wrapped in the test
kit's assertion: the environment, the working directory, ``sys.path`` and the
root logger are as they were when it ends, and the kit's store of opened
secrets lost nothing. Another plugin, or another run in the same process, can
therefore observe nothing the plugin did.

The test stands in the configuration's root before it starts, as a command run
from the root does: the load makes the root the working directory, and that is
the core's doing, put back by the command line when a command ends.
"""
from __future__ import annotations

from harness import copy_config, stub_environment

from cs_image_system.system import testing as kit
from cs_image_system.system.testing import isolation


def test_a_load_and_a_run_of_the_plugin_leave_the_process_as_they_found_it(tmp_path, monkeypatch):
    # the test's own arrangements are made first, so that what the block changes is the plugin's and the core's
    root = copy_config(tmp_path)
    stub_environment(monkeypatch)
    monkeypatch.chdir(root)
    with isolation.process_unchanged():
        ctx = kit.load_context(root)
        summary = kit.drive_lifecycles(ctx, "all", apply=True)
    assert summary.ok, summary.error
    assert {type(gb).__module__.split(".")[1] for gb in ctx.group_builders.values()} >= {"okta_opa_plugin"}
