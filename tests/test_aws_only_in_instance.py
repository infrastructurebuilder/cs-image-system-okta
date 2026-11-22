# SPDX-FileCopyrightText: 2026 Mykel Alvis <mykelalvis@infrastructurebuilder.org>
#
# SPDX-License-Identifier: Apache-2.0

"""The AWS family is the instance suite's, and only the instance suite's.

The suite's machines run on the AWS family, which may change; the plugin
itself never depends on it. So nothing under ``packages/`` and no test outside
``tests/instance/`` imports it, and neither the plugin's dependencies nor its
``test`` extra name one of its distributions (spec 008, FR-004).
"""
from __future__ import annotations

import re
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AWS_MODULES = ("cs_image_system.aws_runtime", "cs_image_system.tf_ebs_instance_plugin",
               "cs_image_system.tf_s3_state_plugin")
AWS_DISTRIBUTIONS = ("cs-image-system-aws-runtime-plugin", "cs-image-system-tf-ebs-instance-plugin",
                     "cs-image-system-tf-s3-state-plugin")
IMPORT = re.compile(r"^\s*(?:from|import)\s+(" + "|".join(re.escape(m) for m in AWS_MODULES) + r")\b", re.M)


def _python_files_outside_the_instance_suite() -> list[Path]:
    instance = REPO / "tests" / "instance"
    tests = [p for p in sorted((REPO / "tests").rglob("*.py")) if not p.is_relative_to(instance)]
    return sorted((REPO / "packages").rglob("*.py")) + tests


def test_no_file_outside_the_instance_suite_imports_the_aws_family():
    offenders = [f"{p.relative_to(REPO)}: {m.group(1)}" for p in _python_files_outside_the_instance_suite()
                 if p != Path(__file__).resolve() for m in IMPORT.finditer(p.read_text())]
    assert offenders == []


def test_the_plugin_names_no_aws_distribution():
    project = tomllib.loads((REPO / "packages" / "okta-opa-plugin" / "pyproject.toml").read_text())["project"]
    named = [*project.get("dependencies", []), *project.get("optional-dependencies", {}).get("test", [])]
    assert [r for r in named if r.startswith(AWS_DISTRIBUTIONS)] == []


def test_only_the_instance_group_names_the_aws_family():
    groups = tomllib.loads((REPO / "pyproject.toml").read_text())["dependency-groups"]
    for name, reqs in groups.items():
        aws = [r for r in reqs if isinstance(r, str) and r.startswith(AWS_DISTRIBUTIONS)]
        assert (name == "instance") == bool(aws), (name, aws)
