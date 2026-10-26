#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Run pinned upstream gclient against tiny local repositories and asset refs."""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


def asset(path, kind, condition=None):
    value = ({"dep_type": "cipd", "packages": [{"package": "fixture/${{platform}}",
               "version": "git_revision:" + "1" * 40}]} if kind == "cipd" else
             {"dep_type": "gcs", "bucket": "ember-source-test-invalid", "objects": [
                 {"object_name": "fixture-object", "sha256sum": "0" * 64,
                  "size_bytes": 1, "generation": 1}]})
    if condition:
        value["condition"] = condition
    return {path: value}


class Acquisition(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="electron-gclient-test-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.workspace = self.root / "workspace"
        (self.workspace / "src").mkdir(parents=True)
        filters = {"GIT_CONFIG_COUNT": "4", "GIT_CONFIG_KEY_0": "filter.lfs.process",
                   "GIT_CONFIG_VALUE_0": "git-lfs filter-process",
                   "GIT_CONFIG_KEY_1": "filter.lfs.required", "GIT_CONFIG_VALUE_1": "true",
                   "GIT_CONFIG_KEY_2": "lfs.fetchinclude", "GIT_CONFIG_VALUE_2": "not-a-fixture",
                   "GIT_CONFIG_KEY_3": "lfs.fetchexclude", "GIT_CONFIG_VALUE_3": "*"}
        self.filters = patch.dict(os.environ, filters)
        self.filters.start()
        self.addCleanup(self.filters.stop)
        self.node, node_pin = self.repo("node", "deps = {}\n")
        self.leaf, leaf_pin = self.repo("leaf", "deps = " + repr(asset("src/leaf/font", "gcs")))
        self.pointer = ("version https://git-lfs.github.com/spec/v1\n"
                        "oid sha256:" + "a" * 64 + "\nsize 1234\n")
        (self.leaf / ".gitattributes").write_text("*.bin filter=lfs diff=lfs merge=lfs -text\n")
        (self.leaf / "asset with space.bin").write_text(self.pointer)
        self.git(self.leaf, "add", ".")
        self.git(self.leaf, "commit", "-qm", "LFS input without an available object")
        leaf_pin = self.git(self.leaf, "rev-parse", "HEAD")
        child_deps = {"src/leaf": self.leaf.as_uri() + "@" + leaf_pin}
        child_deps.update(asset("src/inactive", "gcs", "False"))
        self.chromium, chromium_pin = self.repo("chromium", "deps = " + repr(child_deps) +
                                                "\nrecursedeps = ['src/leaf']\n")
        self.marker = self.root / "hook-ran"
        hook = {"name": "must-not-run", "pattern": ".", "action": [sys.executable, "-c",
                "from pathlib import Path; Path(" + repr(str(self.marker)) + ").write_text('bad')"]}
        deps = ("vars = {'chromium_version': '152.0.7977.167', 'node_version': 'v24.22.1'}\n"
                "deps = {\n'src': {'url': " + repr(self.chromium.as_uri() + "@") +
                " + Var('chromium_version')},\n'src/third_party/electron_node': {'url': " +
                repr(self.node.as_uri() + "@") + " + Var('node_version')},\n")
        for path, value in {**asset("src/package", "cipd"), **asset("src/data", "gcs")}.items():
            deps += repr(path) + ": " + repr(value) + ",\n"
        deps += "}\nrecursedeps = ['src']\nhooks = " + repr([hook]) + "\npre_deps_hooks = " + repr([hook])
        electron, electron_pin = self.repo("electron", deps)
        self.git(self.workspace, "clone", "--no-hardlinks", str(electron), "src/electron")
        pins = patch.multiple(sync.source, ELECTRON_URL=electron.as_uri(), ELECTRON_REVISION=electron_pin,
                              CHROMIUM_URL=self.chromium.as_uri(), CHROMIUM_REVISION=chromium_pin,
                              NODE_URL=self.node.as_uri(), NODE_REVISION=node_pin)
        pins.start()
        self.addCleanup(pins.stop)
        (self.workspace / ".gclient").write_text(sync.source.gclient_config("x64"))
        protocol = patch.dict(os.environ, {"GIT_ALLOW_PROTOCOL": "file"})
        protocol.start()
        self.addCleanup(protocol.stop)

    def git(self, root, *args):
        result = subprocess.run([str(options.git), "-C", str(root), "-c", "user.name=Source Test",
                                 "-c", "user.email=test@example.invalid", *args],
                                capture_output=True, text=True, check=True,
                                env=sync.source_environment(options.git, options.git_lfs, options.source_path))
        return result.stdout.strip()

    def repo(self, name, deps):
        root = self.root / name
        root.mkdir()
        self.git(root, "init", "-q")
        (root / "DEPS").write_text(deps)
        self.git(root, "add", "DEPS")
        self.git(root, "commit", "-qm", "pinned source fixture")
        return root, self.git(root, "rev-parse", "HEAD")

    def run_sync(self):
        try:
            return sync.sync_git(self.workspace, options.depot_tools, options.git,
                                 options.git_lfs, options.source_path, 2)
        except ValueError:
            log = self.workspace / "source-inputs/acquisition.log"
            if log.is_file():
                print(log.read_text()[-12000:])
            raise

    def test_upstream_git_only_sync_and_complete_deferred_inventory(self):
        git_count, pending_count, lfs_count = self.run_sync()
        self.assertEqual((git_count, pending_count, lfs_count), (4, 3, 1))
        self.assertFalse(self.marker.exists(), "gclient hook or prehook executed")
        outputs = self.workspace / "source-inputs"
        pending = json.loads((outputs / "pending-inputs.json").read_text())
        self.assertEqual(set(pending), {"src/package:fixture/${platform}",
                                       "src/data:fixture-object", "src/leaf/font:fixture-object"})
        self.assertEqual(pending["src/leaf/font:fixture-object"]["url"],
                         "gs://ember-source-test-invalid/fixture-object")
        self.assertEqual(pending["src/package:fixture/${platform}"]["rev"], "git_revision:" + "1" * 40)
        self.assertFalse((self.workspace / "src/data").exists())
        self.assertFalse((self.workspace / "src/package").exists())
        actual = json.loads((outputs / "git-revisions.json").read_text())
        self.assertEqual(actual["src"]["rev"], sync.source.CHROMIUM_REVISION)
        self.assertEqual(actual["src/third_party/electron_node"]["rev"], sync.source.NODE_REVISION)
        self.assertEqual(self.git(self.workspace / "src/leaf", "rev-parse", "HEAD"),
                         actual["src/leaf"]["rev"])
        lfs = json.loads((outputs / "pending-lfs.json").read_text())
        self.assertEqual(set(lfs), {"src/leaf"})
        self.assertEqual(lfs["src/leaf"]["rev"], actual["src/leaf"]["rev"])
        self.assertEqual(lfs["src/leaf"]["files"], [{
            "name": "asset with space.bin", "size": 1234, "checkout": False, "downloaded": False,
            "oid_type": "sha256", "oid": "a" * 64, "version": "https://git-lfs.github.com/spec/v1"}])
        self.assertEqual((self.workspace / "src/leaf/asset with space.bin").read_text(), self.pointer)
        self.assertEqual(self.run_sync(), (4, 3, 1), "a Git-only retry must preserve exact inputs")
        self.assertFalse(self.marker.exists())

    def test_upstream_hook_sentinel_is_effective(self):
        self.run_sync()
        result = subprocess.run([sys.executable, "-B", "-E", "-S",
                                 str(options.depot_tools / "gclient.py"), "runhooks", "--jobs", "2"],
                                cwd=self.workspace,
                                env=sync.source_environment(options.git, options.git_lfs, options.source_path),
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.marker.read_text(), "bad")

    def test_changed_workspace_config_refused(self):
        with (self.workspace / ".gclient").open("a") as out:
            out.write("\ncustom = True\n")
        with self.assertRaisesRegex(ValueError, "prepared configuration"):
            self.run_sync()
        self.assertFalse((self.workspace / "source-inputs").exists())

    def test_wrong_depot_tools_pin_refused(self):
        with patch.object(sync.depot_source, "REVISION", "0" * 40):
            with self.assertRaisesRegex(ValueError, "depot_tools HEAD"):
                self.run_sync()

    def test_undeclared_git_refused(self):
        with self.assertRaisesRegex(ValueError, "declared git"):
            sync.source_environment(self.leaf / "DEPS", options.git_lfs, options.source_path)

    def test_undeclared_git_lfs_refused(self):
        with self.assertRaisesRegex(ValueError, "declared git-lfs"):
            sync.source_environment(options.git, self.leaf / "DEPS", options.source_path)

    def test_failed_lfs_inventory_does_not_publish_completion(self):
        self.run_sync()
        with patch.object(sync, "lfs_inventory", side_effect=ValueError("LFS inventory failure")):
            with self.assertRaisesRegex(ValueError, "LFS inventory failure"):
                self.run_sync()
        for name in sync.OUTPUTS:
            self.assertFalse((self.workspace / "source-inputs" / name).exists())

    def test_upstream_lfs_skip_is_effective(self):
        env = sync.source_environment(options.git, options.git_lfs, options.source_path)
        # The local remote has no LFS object. Removing skip must fail instead
        # of silently accepting the pointer; no external server is involved.
        env.update(GIT_CONFIG_VALUE_2="", GIT_CONFIG_VALUE_3="", GIT_CONFIG_COUNT="5",
                   GIT_CONFIG_KEY_4="lfs.url", GIT_CONFIG_VALUE_4=(self.root / "missing-lfs").as_uri())
        with patch.dict(os.environ, env):
            self.assertEqual(self.run_sync(), (4, 3, 1))
        env.pop("GIT_LFS_SKIP_SMUDGE")
        result = subprocess.run([str(options.git_lfs), "smudge", "asset with space.bin"],
                                cwd=self.leaf, env=env, input=self.pointer, capture_output=True, text=True,
                                timeout=15)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Smudge error", result.stderr)

    def test_partial_checkout_retry_preserves_other_repositories(self):
        self.run_sync()
        node_git = self.workspace / "src/third_party/electron_node/.git"
        before = node_git.stat().st_ino
        leaf = self.workspace / "src/leaf"
        # Reproduce checkout interruption after the fetch: objects exist but
        # HEAD has no commit. gclient must quarantine this tree on retry.
        (leaf / ".git/HEAD").write_text("ref: refs/heads/incomplete\n")
        (leaf / "preserved-local-input").write_text("keep me")
        self.assertEqual(self.run_sync(), (4, 3, 1))
        self.assertEqual(node_git.stat().st_ino, before)
        preserved = list((self.workspace / "_bad_scm").rglob("preserved-local-input"))
        self.assertEqual(len(preserved), 1)
        self.assertEqual(preserved[0].read_text(), "keep me")

    def test_simulated_gclient_environment_refused(self):
        with patch.dict(os.environ, {"GCLIENT_TEST": "1"}):
            with self.assertRaisesRegex(ValueError, "GCLIENT_TEST"):
                self.run_sync()


class Inventory(unittest.TestCase):
    def setUp(self):
        self.declared = {
            "src/electron": {"url": sync.source.ELECTRON_URL, "rev": None},
            "src": {"url": sync.source.CHROMIUM_URL, "rev": sync.source.CHROMIUM_REVISION},
            "src/third_party/electron_node": {"url": sync.source.NODE_URL, "rev": sync.source.NODE_REVISION},
        }
        self.actual = {key: dict(value) for key, value in self.declared.items()}
        self.actual["src/electron"]["rev"] = sync.source.ELECTRON_REVISION

    def test_wrong_git_commit_refused(self):
        self.actual["src"]["rev"] = "0" * 40
        with self.assertRaisesRegex(ValueError, "revision differs"):
            sync.check_inventory(self.declared, self.actual)

    def test_mutable_git_revision_refused(self):
        self.declared["src"]["rev"] = "refs/heads/main"
        with self.assertRaisesRegex(ValueError, "full commit"):
            sync.check_inventory(self.declared, self.actual)

    def test_missing_git_dependency_refused(self):
        del self.actual["src"]
        with self.assertRaisesRegex(ValueError, "dependency is missing"):
            sync.check_inventory(self.declared, self.actual)

    def test_missing_required_source_refused(self):
        del self.actual["src"]
        del self.declared["src"]
        with self.assertRaisesRegex(ValueError, "required source pin is missing"):
            sync.check_inventory(self.declared, self.actual)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--git", type=Path, required=True)
    parser.add_argument("--git-lfs", type=Path, required=True)
    parser.add_argument("--depot-tools", type=Path, required=True)
    parser.add_argument("--source-path", required=True)
    options = parser.parse_args()
    helper = Path(__file__).resolve().parents[1] / "electron44/files/sync-git-sources.py"
    spec = importlib.util.spec_from_file_location("electron_git_sync", helper)
    sync = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sync)
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(case)
                               for case in (Acquisition, Inventory))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)
    print("Scope: pinned gclient Git acquisition and deferred-input inventory; no compiler or target execution")
