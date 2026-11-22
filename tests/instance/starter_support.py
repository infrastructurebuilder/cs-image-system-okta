# SPDX-FileCopyrightText: 2026 Mykel Alvis <mykelalvis@infrastructurebuilder.org>
#
# SPDX-License-Identifier: Apache-2.0

"""The system's `standard-aws` starter as a whole tree, for the tests that
read one.

The starters ship inside the installed system (``cs_image_system.system``);
a tree is a skeleton plus an overlay, and its Terraform modules are the
installed plugins'. ``RENDERED()`` writes the one starter this suite needs
(the AWS starter, whose groups are Okta's) once per process and hands back
the directory that holds it, ``<dir>/standard-aws/``. The helper keeps the
name the tests used in cs-image-system-3, from which they moved (spec 008).
"""
from __future__ import annotations

import atexit
import shutil
import subprocess
import tempfile
from pathlib import Path

from cs_image_system.system import starters

#: the one starter the suite renders: its groups are on the Okta builder, its runtime is AWS
STARTER = "standard-aws"

_rendered: Path | None = None


def RENDERED() -> Path:  # noqa: N802 - a constant's name, computed once
    """The installed release's `standard-aws` starter written once per
    process, removed when the process ends."""
    global _rendered
    if _rendered is None:
        into = Path(tempfile.mkdtemp(prefix="csis-starters-"))
        starters.write_starter(STARTER, into / STARTER, version=starters.release_version())
        atexit.register(shutil.rmtree, into, True)
        _rendered = into
    return _rendered


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True).stdout


def _starter_copy(tmp_path: Path, name: str = STARTER, remote: str | None = "git@github.com:acme/widgets.git") -> Path:
    """A rendered starter copied under ``tmp_path/tree`` as a git checkout
    on ``develop``, with ``remote`` as its origin."""
    root = tmp_path / "tree"
    shutil.copytree(RENDERED() / name, root)
    _git(root, "init", "-q", "-b", "develop")
    _git(root, "config", "user.email", "t@example.invalid")
    _git(root, "config", "user.name", "t")
    if remote:
        _git(root, "remote", "add", "origin", remote)
    return root
