#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Test the source guard with real pinned Electron patch tooling and tiny repositories."""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch


class UpstreamPatches(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="electron-upstream-test-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.workspace = self.root / "workspace"
        self.chromium = self.workspace / "src"
        self.node = self.chromium / "third_party/electron_node"
        self.electron = self.chromium / "electron"
        self.base = self.repo(self.chromium)
        self.node_base = self.repo(self.node)
        self.electron.mkdir()
        for relative in ("script/apply_all_patches.py", "script/lib/__init__.py",
                         "script/lib/git.py", "script/lib/patches.py"):
            destination = self.electron / relative
            destination.parent.mkdir(exist_ok=True, parents=True)
            shutil.copyfile(options.electron_source / relative, destination)
        config = [{"repo": "src", "patch_dir": "src/electron/patches/chromium"},
                  {"repo": "src/third_party/electron_node", "patch_dir": "src/electron/patches/node"},
                  {"repo": "src/third_party/squirrel.mac", "patch_dir": "src/electron/patches/squirrel.mac"}]
        self.series(self.chromium, "chromium", ["one\n", "two\n"])
        self.series(self.node, "node", ["node patched\n"])
        (self.electron / "patches/config.json").write_text(json.dumps(config))
        (self.electron / "DEPS").write_text(
            "vars = " + repr({"chromium_version": helper.source.CHROMIUM_VERSION,
                               "node_version": helper.source.NODE_VERSION}) + "\ndeps = " + repr({
                "src": {"url": helper.source.CHROMIUM_URL + "@" + helper.source.CHROMIUM_VERSION},
                "src/third_party/electron_node": {"url": helper.source.NODE_URL + "@" + helper.source.NODE_VERSION}}))
        self.git(self.electron, "init", "-q")
        self.git(self.electron, "add", ".")
        self.git(self.electron, "commit", "-qm", "Electron fixture with production patch tools")
        self.pins = patch.multiple(helper.source, PATCHES=(), ELECTRON_REVISION=self.head(self.electron),
                                   CHROMIUM_REVISION=self.base, NODE_REVISION=self.node_base)
        self.pins.start()
        self.addCleanup(self.pins.stop)
        self.recipe = self.root / "recipe"
        self.recipe.mkdir()
        patch_dir = patch.object(helper, "PATCH_DIR", self.recipe)
        patch_dir.start()
        self.addCleanup(patch_dir.stop)
        self.inputs = self.workspace / "source-inputs"
        self.inputs.mkdir()
        for name in helper.sync.OUTPUTS:
            (self.inputs / name).write_text("{}")
        self.inventory()

    def git(self, root, *args):
        result = subprocess.run([str(options.git), "-C", str(root), "-c", "user.name=Patch Fixture",
                                 "-c", "user.email=fixture@example.invalid", *args],
                                env=helper.sync.source_environment(options.git, options.git_lfs, options.source_path),
                                check=True, capture_output=True, text=True)
        return result.stdout.strip()

    def head(self, root):
        return self.git(root, "rev-parse", "HEAD")

    def repo(self, root):
        root.mkdir(parents=True)
        self.git(root, "init", "-q")
        (root / "source.txt").write_text("base\n")
        self.git(root, "add", "source.txt")
        self.git(root, "commit", "-qm", "base source")
        return self.head(root)

    def series(self, repository, name, values):
        author = self.root / (name + "-author")
        self.git(self.root, "clone", "-q", "--no-hardlinks", str(repository), str(author))
        directory = self.electron / "patches" / name
        directory.mkdir(parents=True)
        files = []
        for number, content in enumerate(values):
            (author / "source.txt").write_text(content)
            self.git(author, "commit", "-qam", f"source change {number}")
            filename = f"change-{number}.patch"
            (directory / filename).write_text(self.git(author, "format-patch", "-1", "--stdout") + "\n")
            files.append(filename)
        (directory / ".patches").write_text("\n".join(files) + "\n")

    def inventory(self):
        declared = {"src/electron": {"url": helper.source.ELECTRON_URL, "rev": None},
                    "src": {"url": helper.source.CHROMIUM_URL, "rev": self.base},
                    "src/third_party/electron_node": {"url": helper.source.NODE_URL, "rev": self.node_base}}
        actual = {name: dict(value) for name, value in declared.items()}
        actual["src/electron"]["rev"] = helper.source.ELECTRON_REVISION
        (self.inputs / "declared-dependencies.json").write_text(json.dumps(declared))
        (self.inputs / "git-revisions.json").write_text(json.dumps(actual))

    def apply(self):
        return helper.apply_upstream(self.workspace, options.git, options.git_lfs, options.source_path)

    def assert_unapplied(self):
        self.assertEqual(self.head(self.chromium), self.base)
        self.assertFalse((self.inputs / "upstream-patches.json").exists())

    def test_real_ordered_series_and_unselected_host_target(self):
        self.assertEqual(self.apply(), (2, ["src/third_party/squirrel.mac"]))
        self.assertEqual((self.chromium / "source.txt").read_text(), "two\n")
        self.assertEqual((self.node / "source.txt").read_text(), "node patched\n")
        self.assertEqual(self.git(self.chromium, "log", "-1", "--format=%an"), "Patch Fixture")
        record = json.loads((self.inputs / "upstream-patches.json").read_text())
        self.assertEqual(record["applied"]["src"], {"base": self.base, "patched": self.head(self.chromium)})
        with self.assertRaisesRegex(ValueError, "HEAD differs"):
            self.apply()

    def test_missing_selected_repository_fails_before_first_patch(self):
        (self.node / ".git").rename(self.root / "preserved-node-git")
        with self.assertRaisesRegex(ValueError, "repository is missing"):
            self.apply()
        self.assert_unapplied()

    def test_changed_target_pin_fails_before_first_patch(self):
        self.git(self.node, "commit", "--allow-empty", "-qm", "wrong pin")
        with self.assertRaisesRegex(ValueError, "HEAD differs"):
            self.apply()
        self.assert_unapplied()

    def test_dirty_target_fails_before_first_patch(self):
        (self.node / "source.txt").write_text("local edits\n")
        with self.assertRaisesRegex(ValueError, "tracked changes"):
            self.apply()
        self.assert_unapplied()

    def test_incomplete_acquisition_refused(self):
        (self.inputs / "pending-lfs.json").unlink()
        with self.assertRaisesRegex(ValueError, "complete Git acquisition"):
            self.apply()
        self.assert_unapplied()

    def test_changed_upstream_config_refused(self):
        (self.electron / "patches/config.json").write_text("[]")
        with self.assertRaisesRegex(ValueError, "recipe-prepared"):
            self.apply()
        self.assert_unapplied()

    def test_changed_upstream_tool_refused(self):
        with (self.electron / "script/lib/git.py").open("a") as out:
            out.write("\n# untracked implementation delta\n")
        with self.assertRaisesRegex(ValueError, "recipe-prepared"):
            self.apply()
        self.assert_unapplied()

    def test_edited_upstream_patch_refused_before_first_target(self):
        with (self.electron / "patches/chromium/change-0.patch").open("a") as out:
            out.write("\nunauthorized source delta\n")
        with self.assertRaisesRegex(ValueError, "recipe-prepared"):
            self.apply()
        self.assert_unapplied()

    def test_staged_upstream_order_change_refused_before_first_target(self):
        (self.electron / "patches/chromium/.patches").write_text("change-1.patch\nchange-0.patch\n")
        self.git(self.electron, "add", "patches/chromium/.patches")
        with self.assertRaisesRegex(ValueError, "recipe-prepared"):
            self.apply()
        self.assert_unapplied()

    def test_three_way_fallback_refused(self):
        with patch.dict(os.environ, {"ELECTRON_USE_THREE_WAY_MERGE_FOR_PATCHES": ""}):
            with self.assertRaisesRegex(ValueError, "three-way"):
                self.apply()
        self.assert_unapplied()

    def test_wrong_series_order_fails_and_retains_partial_state(self):
        (self.electron / "patches/chromium/.patches").write_text("change-1.patch\nchange-0.patch\n")
        self.git(self.electron, "commit", "-qam", "causal invalid patch series")
        with patch.object(helper.source, "ELECTRON_REVISION", self.head(self.electron)):
            self.inventory()
            with self.assertRaisesRegex(ValueError, "upstream patches failed"):
                self.apply()
        self.assertTrue((self.chromium / ".git/rebase-apply").is_dir())
        self.assert_unapplied()
        self.assertEqual(self.head(self.node), self.node_base)


class ProductionRecipe(unittest.TestCase):
    def test_real_prepared_security_roll_matches_expected_tree(self):
        with tempfile.TemporaryDirectory(prefix="electron-production-tree-") as temporary:
            electron = helper.source.prepare(options.electron_source, Path(temporary) / "workspace",
                                              options.git, "x64", helper.PATCH_DIR)
            env = helper.sync.source_environment(options.git, options.git_lfs, options.source_path)
            before = helper.source.git_run(options.git, electron, "write-tree")
            helper.verify_electron(electron, options.git, env)
            self.assertEqual(helper.source.git_run(options.git, electron, "write-tree"), before)
            self.assertTrue(helper.source.git_run(options.git, electron, "diff", "--cached", "--", "patches/node"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--git", type=Path, required=True)
    parser.add_argument("--git-lfs", type=Path, required=True)
    parser.add_argument("--source-path", required=True)
    parser.add_argument("--electron-source", type=Path, required=True)
    options = parser.parse_args()
    path = Path(__file__).resolve().parents[1] / "electron44/files/apply-upstream-patches.py"
    spec = importlib.util.spec_from_file_location("electron_upstream_patches", path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.source.require(helper.source.git_run(options.git, options.electron_source, "rev-parse", "HEAD") ==
                          helper.source.ELECTRON_REVISION, "test tooling must come from the pinned Electron source")
    helper.source.require(not helper.source.git_run(options.git, options.electron_source, "status", "--porcelain"),
                          "test Electron source must be clean")
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(case)
                               for case in (UpstreamPatches, ProductionRecipe))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)
    print("Scope: real upstream patch CLI and source guard; no source download, compiler or target execution")
