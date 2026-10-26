#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Test shared depot_tools preparation and interrupted SYNC checkout recovery."""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


class SharedSource(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="shared-depot-tools-")
        cls.root = Path(cls.tmp.name)
        cls.prepared = owner.prepare(options.source, cls.root / "prepared", options.git)
        cls.addClassCleanup(cls.tmp.cleanup)

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="depot-tools-source-test-")
        self.addCleanup(temporary.cleanup)
        self.work = Path(temporary.name)
        self.env = dict(os.environ, PATH=options.source_path, GIT_ALLOW_PROTOCOL="file",
                        DEPOT_TOOLS_UPDATE="0", DEPOT_TOOLS_METRICS="0", GIT_LFS_SKIP_SMUDGE="1")
        for name in ("GCLIENT_FILE", "GIT_CACHE_PATH", "PYTHONPATH", "PYTHONHOME", "GIT_INDEX_FILE"):
            self.env.pop(name, None)

    def git(self, path, *args):
        return subprocess.run([str(options.git), "-C", str(path), "-c", "user.name=Source Fixture",
                               "-c", "user.email=fixture@example.invalid", *args], env=self.env,
                              capture_output=True, text=True, check=True).stdout.strip()

    def repository(self, name, deps="deps = {}\n"):
        root = self.work / name
        root.mkdir()
        self.git(root, "init", "-q")
        (root / "DEPS").write_text(deps)
        self.git(root, "add", "DEPS")
        self.git(root, "commit", "-qm", "source fixture")
        return root, self.git(root, "rev-parse", "HEAD")

    def gclient(self, tools, workspace, command, *args):
        return subprocess.run([sys.executable, "-B", "-E", "-S", str(tools / "gclient.py"), command,
                               *args], cwd=workspace, env=self.env, capture_output=True, text=True)

    def test_exact_shared_preparation_preserves_source(self):
        owner.verify_prepared(self.prepared, options.git)
        self.assertEqual(self.git(options.source, "status", "--porcelain", "--untracked-files=all"), "")
        self.assertEqual(self.git(self.prepared, "remote", "get-url", "origin"), owner.URL)
        self.assertIn("gclient_scm.py", self.git(self.prepared, "diff", "--cached", "--name-only"))

    def test_raw_upstream_is_not_the_prepared_tool(self):
        with self.assertRaisesRegex(ValueError, "shared source patches"):
            owner.verify_prepared(options.source, options.git)

    def test_changed_prepared_tool_refused(self):
        own = owner.prepare(options.source, self.work / "changed", options.git)
        with (own / "gclient_scm.py").open("a") as out:
            out.write("\n# changed tool\n")
        with self.assertRaisesRegex(ValueError, "unstaged changes"):
            owner.verify_prepared(own, options.git)

    def test_wrong_pin_refused(self):
        with patch.object(owner, "REVISION", "0" * 40):
            with self.assertRaisesRegex(ValueError, "shared source pin"):
                owner.prepare(options.source, self.work / "wrong", options.git)
        self.assertFalse((self.work / "wrong").exists())

    def test_incomplete_patch_order_refused(self):
        with patch.object(owner, "PATCHES", ()):
            with self.assertRaisesRegex(ValueError, "complete patch directory"):
                owner.verify_prepared(self.prepared, options.git)

    def test_revinfo_preserves_complete_cipd_version_without_acquiring_assets(self):
        version = "version:3@4.60.4"
        parent, pin = self.repository("parent", "deps = " + repr({
            "src/asset": {"dep_type": "cipd", "packages": [{
                "package": "example/rollup/${{platform}}", "version": version}]},
        }) + "\n")
        workspace = self.work / "workspace"
        workspace.mkdir()
        self.git(workspace, "clone", "-q", "--no-hardlinks", str(parent), "src")
        (workspace / ".gclient").write_text("solutions = " + repr([{
            "name": "src", "url": parent.as_uri() + "@" + pin, "managed": False}]) + "\n")
        inventories = []
        for label, tools in (("upstream", options.source), ("prepared", self.prepared)):
            output = workspace / (label + ".json")
            result = self.gclient(tools, workspace, "revinfo", "--output-json", str(output))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            inventories.append(json.loads(output.read_text()))
        baseline, fixed = inventories
        key = "src/asset:example/rollup/${platform}"
        self.assertEqual(baseline[key]["rev"], "version:3")
        self.assertEqual(fixed[key]["rev"], version)
        self.assertEqual(fixed[key]["url"], baseline[key]["url"])
        self.assertEqual(fixed["src"], baseline["src"])
        self.assertEqual(fixed["src"]["rev"], pin)
        self.assertFalse((workspace / "src/asset").exists())

    def test_sync_gitlink_recovers_broken_head_and_preserves_other_inputs(self):
        leaf, leaf_pin = self.repository("leaf")
        node, node_pin = self.repository("node")
        parent, _ = self.repository("parent", "git_dependencies = 'SYNC'\ndeps = " + repr({
            "src/leaf": leaf.as_uri() + "@" + leaf_pin,
            "src/node": node.as_uri() + "@" + node_pin}) + "\n")
        self.git(parent, "update-index", "--add", "--cacheinfo", f"160000,{leaf_pin},leaf")
        self.git(parent, "commit", "-qm", "parent gitlink")
        workspace = self.work / "workspace"
        workspace.mkdir()
        self.git(workspace, "clone", "-q", "--no-hardlinks", str(parent), "src")
        (workspace / ".gclient").write_text("solutions = " + repr([{
            "name": "src", "url": parent.as_uri(), "managed": False}]) + "\n")
        flags = ("--nohooks", "--noprehooks", "--no-history", "--no-bootstrap",
                 "--ignore-dep-type=cipd", "--ignore-dep-type=gcs", "--jobs", "2")
        result = self.gclient(options.source, workspace, "sync", *flags)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        child = workspace / "src/leaf"
        node_git = workspace / "src/node/.git"
        node_inode = node_git.stat().st_ino
        node_packs = sorted(p.name for p in (node_git / "objects/pack").glob("*.pack"))
        # This is the state left after a fetch followed by failed checkout.
        (child / ".git/HEAD").write_text("ref: refs/heads/interrupted\n")
        (child / ".git/index").unlink()
        (child / "unique-local-input").write_text("preserve this\n")
        baseline = self.gclient(options.source, workspace, "sync", *flags)
        self.assertEqual(baseline.returncode, 0, baseline.stdout + baseline.stderr)
        baseline_info = self.gclient(options.source, workspace, "revinfo", "--actual", *flags[-4:])
        self.assertNotEqual(baseline_info.returncode, 0)
        self.assertIn("rev-parse HEAD", baseline_info.stderr)
        fixed = self.gclient(self.prepared, workspace, "sync", *flags)
        self.assertEqual(fixed.returncode, 0, fixed.stdout + fixed.stderr)
        self.assertEqual(self.git(child, "rev-parse", "HEAD"), leaf_pin)
        self.assertEqual(self.git(workspace / "src/node", "rev-parse", "HEAD"), node_pin)
        self.assertEqual(node_git.stat().st_ino, node_inode)
        self.assertEqual(sorted(p.name for p in (node_git / "objects/pack").glob("*.pack")), node_packs)
        saved = list((workspace / "_bad_scm").rglob("unique-local-input"))
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0].read_text(), "preserve this\n")
        inventory = workspace / "actual.json"
        actual = self.gclient(self.prepared, workspace, "revinfo", "--actual", "--output-json", str(inventory))
        self.assertEqual(actual.returncode, 0, actual.stdout + actual.stderr)
        self.assertEqual(json.loads(inventory.read_text())["src/leaf"]["rev"], leaf_pin)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--git", type=Path, required=True)
    parser.add_argument("--source-path", required=True)
    options = parser.parse_args()
    selected_git = shutil.which("git", path=options.source_path)
    if not selected_git or Path(selected_git).resolve() != options.git.resolve():
        parser.error("--source-path must resolve the declared Git")
    spec = importlib.util.spec_from_file_location("depot_tools_source", Path(__file__).with_name("source.py"))
    owner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(owner)
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SharedSource))
    if not result.wasSuccessful():
        raise SystemExit(1)
    print("Scope: shared source preparation and real Git-only recovery; no external downloads or compiler use")
