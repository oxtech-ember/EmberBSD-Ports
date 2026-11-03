#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Acquire Electron's Git dependencies; retain deferred CIPD/GCS/LFS inputs."""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

FILTERS = ("--ignore-dep-type=cipd", "--ignore-dep-type=gcs")
OUTPUTS = ("sync.json", "declared-dependencies.json", "git-revisions.json", "pending-inputs.json",
           "pending-lfs.json")

spec = importlib.util.spec_from_file_location(
    "electron_source_prepare", Path(__file__).with_name("prepare-sources.py"))
source = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source)
require = source.require

def load_depot_source(owner=None):
    # The recipe's patch/build stages also import this module. They do not
    # consume depot_tools and must work when exported outside the Ports tree.
    if owner is None:
        owner = Path(__file__).resolve().parents[4] / "scripts/source-inputs/depot-tools/source.py"
    owner = Path(owner)
    require(owner.is_absolute() and owner.is_file(),
            "--depot-tools-owner must name the shared Ports depot_tools source.py")
    spec = importlib.util.spec_from_file_location("shared_depot_tools_source", owner)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(callable(getattr(module, "verify_prepared", None)),
            "depot_tools source owner does not provide verify_prepared")
    return module


def source_environment(git, git_lfs, source_path):
    directories = source_path.split(os.pathsep)
    require(all(item and Path(item).is_absolute() and Path(item).is_dir()
                for item in directories), "--source-path must contain explicit absolute directories")
    for name, executable in (("git", git), ("git-lfs", git_lfs)):
        require(Path(executable).is_absolute() and Path(executable).is_file(),
                f"--{name} must name an absolute executable")
        found = shutil.which(name, path=source_path)
        require(found and Path(found).resolve() == Path(executable).resolve(),
                f"--source-path must resolve the declared {name} executable")
    require(not os.environ.get("GCLIENT_TEST"), "GCLIENT_TEST is not a source acquisition input")
    env = os.environ.copy()
    env.update(PATH=source_path, DEPOT_TOOLS_UPDATE="0", DEPOT_TOOLS_METRICS="0",
               GIT_LFS_SKIP_SMUDGE="1")
    # Select the prepared .gclient and avoid an undeclared shared cache writer.
    for name in ("GCLIENT_FILE", "GIT_CACHE_PATH", "PYTHONPATH", "PYTHONHOME"):
        env.pop(name, None)
    return env


def verify_inputs(workspace, depot_tools, git, depot_tools_owner=None):
    load_depot_source(depot_tools_owner).verify_prepared(depot_tools, git)
    config = (workspace / ".gclient").read_text(encoding="utf-8")
    require(config in (source.gclient_config("arm64"), source.gclient_config("x64")),
            "workspace .gclient differs from the recipe's prepared configuration")
    electron = workspace / "src/electron"
    require(source.git_run(git, electron, "rev-parse", "HEAD") == source.ELECTRON_REVISION,
            "Electron HEAD does not match the recipe pin")
    source.check_deps(electron / "DEPS", source.NODE_VERSION)


def check_inventory(declared, actual):
    """Compare Git pins and preserve every selected non-Git declaration."""
    pending = {}
    for name, item in declared.items():
        url = item["url"]
        if not url:
            continue
        if url.startswith(("gs://", "https://chrome-infra-packages.appspot.com/")):
            require(name not in actual, f"non-Git input unexpectedly present in Git inventory: {name}")
            pending[name] = item
            continue
        require(name in actual, f"Git dependency is missing: {name}")
        require(actual[name]["url"] == url, f"Git dependency URL changed: {name}")
        revision = source.ELECTRON_REVISION if name == "src/electron" else item["rev"]
        require(isinstance(revision, str) and re.fullmatch(r"[0-9a-f]{40}", revision),
                f"Git dependency is not pinned to a full commit: {name}")
        require(actual[name]["rev"] == revision, f"Git dependency revision differs: {name}")
    require(set(actual) <= set(declared), "Git inventory has undeclared dependencies")
    for name, revision in (("src", source.CHROMIUM_REVISION),
                           ("src/third_party/electron_node", source.NODE_REVISION)):
        require(actual.get(name, {}).get("rev") == revision, f"required source pin is missing: {name}")
    return pending


def lfs_inventory(workspace, actual, git_lfs, env):
    """Ask upstream Git LFS for the nonempty object pointers at each pinned HEAD."""
    pending = {}
    for name, repository in sorted(actual.items()):
        root = (workspace / name).resolve(strict=True)
        require(root.is_relative_to(workspace), f"Git dependency escapes the workspace: {name}")
        result = subprocess.run([str(git_lfs), "ls-files", "--json", "--include=", "--exclude=", "HEAD"],
                                cwd=root, env=env, capture_output=True, text=True)
        require(result.returncode == 0, f"Git LFS inventory failed for {name}: {result.stderr.strip()}")
        files = json.loads(result.stdout)["files"] or []
        if files:
            pending[name] = {**repository, "files": files}
    return pending


def sync_git(workspace, depot_tools, git, git_lfs, source_path, jobs, *, depot_tools_owner=None):
    workspace = Path(workspace).resolve(strict=True)
    depot_tools = Path(depot_tools).resolve(strict=True)
    git = Path(git)
    require(git.is_absolute() and git.is_file(), "--git must name an absolute executable")
    require(jobs >= 1, "--jobs must be positive")
    env = source_environment(git, git_lfs, source_path)
    verify_inputs(workspace, depot_tools, git, depot_tools_owner)
    outputs = workspace / "source-inputs"
    require(not outputs.is_symlink(), "source-inputs must not be a symlink")
    outputs.mkdir(exist_ok=True)
    # These are recipe-owned inventories, not build acceptance records. Remove
    # old completion data before retrying; keep the source tree and log intact.
    for name in OUTPUTS:
        (outputs / name).unlink(missing_ok=True)
    command = [sys.executable, "-B", "-E", "-S", str(depot_tools / "gclient.py")]
    with tempfile.TemporaryDirectory(prefix=".inventory-", dir=outputs) as temporary:
        stage = Path(temporary)
        commands = [
            [*command, "sync", "--nohooks", "--noprehooks", "--no-history", "--no-bootstrap",
             *FILTERS, "--jobs", str(jobs), "--output-json", str(stage / "sync.json")],
            # Default revinfo reads declarations only. --actual without the
            # filters would query CIPD; flatten can download GCS inputs.
            [*command, "revinfo", "--jobs", str(jobs),
             "--output-json", str(stage / "declared-dependencies.json")],
            [*command, "revinfo", "--actual", *FILTERS, "--jobs", str(jobs),
             "--output-json", str(stage / "git-revisions.json")],
        ]
        with (outputs / "acquisition.log").open("a", encoding="utf-8") as log:
            for argv in commands:
                log.write("\nargv: " + json.dumps(argv) + "\n")
                log.flush()
                print("Running gclient " + argv[5], flush=True)
                result = subprocess.run(argv, cwd=workspace, env=env, stdout=log, stderr=subprocess.STDOUT)
                require(result.returncode == 0,
                        f"gclient {argv[5]} failed ({result.returncode}); see {log.name}")
        declared = json.loads((stage / "declared-dependencies.json").read_text())
        actual = json.loads((stage / "git-revisions.json").read_text())
        pending = check_inventory(declared, actual)
        lfs = lfs_inventory(workspace, actual, git_lfs, env)
        (stage / "pending-lfs.json").write_text(json.dumps(lfs, indent=2, sort_keys=True) + "\n")
        (stage / "pending-inputs.json").write_text(json.dumps(pending, indent=2, sort_keys=True) + "\n")
        for name in OUTPUTS:
            (stage / name).replace(outputs / name)
    return len(actual), len(pending), sum(len(repo["files"]) for repo in lfs.values())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--depot-tools", type=Path, required=True)
    parser.add_argument("--depot-tools-owner", type=Path,
                        help="shared Ports scripts/source-inputs/depot-tools/source.py; required outside Ports")
    parser.add_argument("--git", type=Path, required=True)
    parser.add_argument("--git-lfs", type=Path, required=True)
    parser.add_argument("--source-path", required=True,
                        help="explicit PATH for source tools, including the selected Git and Git LFS")
    parser.add_argument("--jobs", type=int, required=True)
    args = parser.parse_args()
    try:
        git_count, pending_count, lfs_count = sync_git(
            args.workspace, args.depot_tools, args.git, args.git_lfs, args.source_path, args.jobs,
            depot_tools_owner=args.depot_tools_owner)
    except (ValueError, OSError, SyntaxError) as exc:
        parser.exit(1, f"Git source acquisition failed: {exc}\n")
    print(f"Git sources acquired: {git_count}; deferred CIPD/GCS entries: {pending_count}; "
          f"LFS object inputs: {lfs_count}")
    print("Hooks, upstream patches, BSD overlays and compilation have not run.")


if __name__ == "__main__":
    main()
