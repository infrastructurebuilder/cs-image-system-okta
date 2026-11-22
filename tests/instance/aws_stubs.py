# SPDX-FileCopyrightText: 2026 Mykel Alvis <mykelalvis@infrastructurebuilder.org>
#
# SPDX-License-Identifier: Apache-2.0

"""The AWS stubs the instance suite's machines run on.

TEMPORARY: a copy of the AWS stubs of cs-image-system-3's shared harness
(``tests/harness.py``, at the commit spec 008 moved the plugin from), kept
here until spec 007's phase 1 publishes ``cs_image_system.aws_runtime.testing``,
which replaces this file (spec 008, research R3). Nothing here reaches AWS: the
networking discovery, the vendor image query, the image listing, the retagging
and the session command are answered in-process.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from cs_image_system.contract.constants import OOPS_DEFAULTS
from cs_image_system.system.testing import FIXED_CHECKED_AT, passing_session

VPCS = ["vpc-0c78d0d63b7a100df", "vpc-0381e9f82c9ae68e7", "default"]
VENDOR_AMI = "ami-0feedfacecafebeef"


class _AnySecurityGroups(dict):
    """Stubbed account SG map: membership always true. Which security groups
    exist is a live-account fact; the fixture's configured ids are data, not
    values these tests should restate."""
    def __contains__(self, key: object) -> bool:
        return True


def record_network_facts(root: Path, checked_at: str = FIXED_CHECKED_AT) -> Path:
    """Write ``<root>/meta-state/runtime-facts.yaml`` for the tree under
    ``root``, derived from its own ``cfg/*.yml``: every aws runtime's declared
    network (a `default` recorded as the literal ``default``, what the stubs
    answer as the account's default), its declared subnet ids and its declared
    security groups -- as if a real run had checked them. The path is returned."""
    runtimes: dict[str, dict] = {}
    for p in sorted((root / "cfg").glob("*.y*ml")):
        doc = yaml.safe_load(p.read_text()) or {}
        for r in (doc.get("runtime_builders") or []) if isinstance(doc, dict) else []:
            if not isinstance(r, dict) or r.get("type") != "aws" or not r.get("name"):
                continue
            net = r.get("networking") or {}
            network = net.get("network")
            facts: dict = {"network": "default" if network in OOPS_DEFAULTS else str(network),
                           "subnets": [str(s.get("subnet_id")) for s in net.get("subnets") or []],
                           "security_groups": [str(sg) for sg in net.get("addl_security_groups") or []]}
            facts["checked_at"] = checked_at
            runtimes[str(r["name"])] = facts
    path = root / "meta-state" / "runtime-facts.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"runtimes": runtimes}, sort_keys=True, default_flow_style=False))
    return path


def stub(monkeypatch, retags: list[tuple[str, dict[str, str]]]) -> None:
    """The AWS stubs. A LOAD never calls them (the copy's
    meta-state/runtime-facts.yaml says what they would answer), but a real
    run's `discover` and a test's `validate --online` do, and get the same
    answers."""
    from cs_image_system.aws_runtime import aws_utils
    monkeypatch.setattr(aws_utils, "get_vpc_map_and_default_vpc_id",
                        lambda session_config: ({v: {"subnets": []} for v in VPCS}, "default",
                                                _AnySecurityGroups()))
    from cs_image_system.aws_runtime.aws_runtime_builders import AwsCloudBuilder
    monkeypatch.setattr(AwsCloudBuilder, "query_provider_image",
                        lambda self, osb: (VENDOR_AMI, "amazon", {}))
    # the read-only state-query hooks would reach AWS: answer "nothing of ours
    # exists" by default; tests of the query itself re-patch these AFTER
    # constructing their FixtureRun
    monkeypatch.setattr(AwsCloudBuilder, "query_images", lambda self, series: [])
    # post-bake retagging would reach EC2; journal it
    monkeypatch.setattr(AwsCloudBuilder, "retag_image",
                        lambda self, image_id, tags: retags.append((image_id, dict(tags))) or True)
    # the post-bake suite runs over the session command; the stub answers PASS
    # for every assertion the script carries (tests that need a failing or dead
    # session override this per test)
    monkeypatch.setattr(AwsCloudBuilder, "run_session_command",
                        passing_session(AwsCloudBuilder.run_session_command))
