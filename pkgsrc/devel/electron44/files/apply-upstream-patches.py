#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Apply Electron's upstream patch series to its selected, pinned Git sources."""

import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

spec = importlib.util.spec_from_file_location(
    "electron_git_sources", Path(__file__).with_name("sync-git-sources.py"))
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)
source = sync.source
require = source.require
PATCH_DIR = Path(__file__).resolve().parents[1] / "patches"


def verify_electron(electron, git, env):
    require(source.git_run(git, electron, "rev-parse", "HEAD", env=env) == source.ELECTRON_REVISION,
            "Electron HEAD differs from the recipe pin")
    source.check_deps(electron / "DEPS", source.NODE_VERSION)
    # Reconstruct the recipe-prepared tree in a separate index, including the
    # Node security roll's upstream patch edits. Never reapply to the work tree.
    with tempfile.TemporaryDirectory(prefix="electron-expected-index-") as temporary:
        expected_env = dict(env, GIT_INDEX_FILE=str(Path(temporary) / "index"))
        source.git_run(git, electron, "read-tree", source.ELECTRON_REVISION, env=expected_env)
        for patch in source.ordered_patches(PATCH_DIR):
            source.git_run(git, electron, "apply", "--cached", "--check", str(patch), env=expected_env)
            source.git_run(git, electron, "apply", "--cached", str(patch), env=expected_env)
        expected = source.git_run(git, electron, "write-tree", env=expected_env)
    require(source.git_run(git, electron, "write-tree", env=env) == expected,
            "Electron index differs from the recipe-prepared source tree")
    require(not source.git_run(git, electron, "diff", "--name-only", env=env),
            "Electron has unstaged changes to the recipe-prepared source tree")
    require(not source.git_run(git, electron, "ls-files", "--others", "--exclude-standard", env=env),
            "Electron has untracked inputs outside the recipe-prepared source tree")


def selected_targets(workspace, git, env):
    inputs = workspace / "source-inputs"
    require(all((inputs / name).is_file() for name in sync.OUTPUTS),
            "complete Git acquisition inventories are required")
    declared = json.loads((inputs / "declared-dependencies.json").read_text())
    actual = json.loads((inputs / "git-revisions.json").read_text())
    sync.check_inventory(declared, actual)
    electron = workspace / "src/electron"
    verify_electron(electron, git, env)
    config = json.loads((electron / "patches/config.json").read_text())
    selected, inactive = [], []
    seen = set()
    for target in config:
        name = target["repo"]
        require(name not in seen, f"duplicate upstream patch target: {name}")
        seen.add(name)
        if name not in declared:
            # Upstream DEPS conditions can exclude Mac-only patch targets on
            # another host. Distinguish them from missing selected checkouts.
            inactive.append(name)
            continue
        require(name in actual, f"selected patch target is not a Git dependency: {name}")
        root = (workspace / name).resolve()
        require(root.is_relative_to(workspace) and (root / ".git").exists(),
                f"selected patch repository is missing: {name}")
        require(Path(source.git_run(git, root, "rev-parse", "--show-toplevel", env=env)).resolve() == root,
                f"patch target is not its own repository: {name}")
        require(source.git_run(git, root, "rev-parse", "HEAD", env=env) == actual[name]["rev"],
                f"patch target HEAD differs from its acquisition pin: {name}")
        require(not source.git_run(git, root, "status", "--porcelain", "--untracked-files=no", env=env),
                f"patch target has tracked changes: {name}")
        patch_dir = (workspace / target["patch_dir"]).resolve(strict=True)
        require(patch_dir.is_relative_to(electron / "patches"),
                f"patch directory escapes Electron's patch series: {name}")
        require((patch_dir / ".patches").is_file(), f"ordered patch list is missing: {name}")
        selected.append(target)
    return selected, inactive, actual


def apply_upstream(workspace, git, git_lfs, source_path):
    workspace = Path(workspace).resolve(strict=True)
    env = sync.source_environment(git, git_lfs, source_path)
    require("ELECTRON_USE_THREE_WAY_MERGE_FOR_PATCHES" not in env,
            "three-way patch fallback is not a recipe input")
    env.pop("GIT_INDEX_FILE", None)
    selected, inactive, actual = selected_targets(workspace, git, env)
    inputs = workspace / "source-inputs"
    output = inputs / "upstream-patches.json"
    require(not output.exists(), "upstream patches already have a completed inventory")
    applied = {}
    script = workspace / "src/electron/script/apply_all_patches.py"
    with tempfile.TemporaryDirectory(prefix=".patch-config-", dir=inputs) as temporary:
        config = Path(temporary) / "config.json"
        with (inputs / "upstream-patches.log").open("a", encoding="utf-8") as log:
            for target in selected:
                # Keep upstream's CLI and patch-list order. A single target per
                # invocation bounds source preparation to one repository writer.
                config.write_text(json.dumps([target]) + "\n")
                argv = [sys.executable, "-B", "-E", "-S", str(script), str(config)]
                log.write("\ntarget: " + json.dumps(target) + "\nargv: " + json.dumps(argv) + "\n")
                log.flush()
                print("Applying upstream patches: " + target["repo"], flush=True)
                result = subprocess.run(argv, cwd=workspace, env=env, stdout=log, stderr=subprocess.STDOUT)
                require(result.returncode == 0,
                        f"upstream patches failed for {target['repo']}; see {log.name}; partial state retained")
                applied[target["repo"]] = {
                    "base": actual[target["repo"]]["rev"],
                    "patched": source.git_run(git, workspace / target["repo"], "rev-parse", "HEAD", env=env),
                }
        completion = Path(temporary) / "upstream-patches.json"
        completion.write_text(json.dumps({"applied": applied, "unselected": inactive}, indent=2, sort_keys=True) + "\n")
        completion.replace(output)
    return len(applied), inactive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--git", type=Path, required=True)
    parser.add_argument("--git-lfs", type=Path, required=True)
    parser.add_argument("--source-path", required=True)
    args = parser.parse_args()
    try:
        count, inactive = apply_upstream(args.workspace, args.git, args.git_lfs, args.source_path)
    except (ValueError, OSError, SyntaxError) as exc:
        parser.exit(1, f"Upstream patch preparation failed: {exc}\n")
    print(f"Upstream patch repositories prepared: {count}; unselected: {', '.join(inactive) or 'none'}")
    print("CIPD/GCS/LFS payloads, BSD adaptations, generators and compilation remain separate stages.")


if __name__ == "__main__":
    main()
