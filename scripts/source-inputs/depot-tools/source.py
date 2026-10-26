#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Prepare the shared pinned depot_tools source input without an installed SDK."""

import argparse
import os
from pathlib import Path
import subprocess
import tempfile

URL = "https://chromium.googlesource.com/chromium/tools/depot_tools.git"
REVISION = "b86fc981b72ab966f8260f73b4eca600b3b12677"
PATCHES = ("patch-gclient_scm.py",)
PATCH_DIR = Path(__file__).resolve().parent / "patches"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def git_run(git, root, *args, env=None):
    if env is None:
        env = os.environ.copy()
        env.pop("GIT_INDEX_FILE", None)
    result = subprocess.run([str(git), "-C", str(root), *args], env=env, capture_output=True, text=True)
    require(result.returncode == 0, f"git {args[0]} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def ordered_patches():
    patches = [PATCH_DIR / name for name in PATCHES]
    require(all(path.is_file() for path in patches), "depot_tools recipe patch is missing")
    require(len(set(PATCHES)) == len(PATCHES) and
            set(PATCHES) == {path.name for path in PATCH_DIR.glob("patch-*")},
            "depot_tools recipe patch order must cover its complete patch directory")
    return patches


def verify_prepared(root, git):
    root = Path(root).resolve(strict=True)
    require(Path(git_run(git, root, "rev-parse", "--show-toplevel")).resolve() == root,
            "depot_tools must be its own Git repository")
    require(git_run(git, root, "rev-parse", "HEAD") == REVISION,
            "depot_tools HEAD does not match its shared source pin")
    with tempfile.TemporaryDirectory(prefix="depot-tools-index-") as temporary:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(temporary) / "index"))
        git_run(git, root, "read-tree", REVISION, env=env)
        for patch in ordered_patches():
            git_run(git, root, "apply", "--cached", "--check", str(patch), env=env)
            git_run(git, root, "apply", "--cached", str(patch), env=env)
        expected = git_run(git, root, "write-tree", env=env)
    require(git_run(git, root, "write-tree") == expected,
            "depot_tools index differs from its shared source patches")
    require(not git_run(git, root, "diff", "--name-only"), "depot_tools has unstaged changes")
    require(not git_run(git, root, "ls-files", "--others", "--exclude-standard"),
            "depot_tools has untracked source inputs")


def prepare(source, destination, git):
    source = Path(source).resolve(strict=True)
    destination = Path(destination).absolute()
    require(Path(git).is_absolute() and Path(git).is_file(), "--git must be an absolute executable")
    require(not destination.exists() and not destination.is_symlink(), "destination must be new")
    destination = destination.parent.resolve(strict=True) / destination.name
    require(not destination.is_relative_to(source), "destination must be outside source")
    require(Path(git_run(git, source, "rev-parse", "--show-toplevel")).resolve() == source,
            "source must be the depot_tools repository root")
    require(git_run(git, source, "rev-parse", "HEAD") == REVISION,
            "depot_tools HEAD does not match its shared source pin")
    require(not git_run(git, source, "status", "--porcelain", "--untracked-files=all"),
            "depot_tools input must be clean")
    patches = ordered_patches()
    destination.mkdir()
    git_run(git, destination.parent, "clone", "--no-hardlinks", "--dissociate", "--no-checkout",
            str(source), str(destination))
    git_run(git, destination, "checkout", "--detach", REVISION)
    git_run(git, destination, "remote", "set-url", "origin", URL)
    for patch in patches:
        git_run(git, destination, "apply", "--check", "--index", str(patch))
        git_run(git, destination, "apply", "--index", str(patch))
    verify_prepared(destination, git)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--git", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = prepare(args.source, args.destination, args.git)
    except (ValueError, OSError) as exc:
        parser.exit(1, f"depot_tools preparation failed: {exc}\n")
    print(f"Prepared shared depot_tools source: {result}")
    print("No dependency sync, hooks, assets, package installation or compiler execution ran.")


if __name__ == "__main__":
    main()
