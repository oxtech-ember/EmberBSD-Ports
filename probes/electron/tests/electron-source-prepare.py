#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Exercise source preparation with real Git, without fetching dependencies."""

import argparse
import ast
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

DEPS = """vars = {
    'chromium_version': '152.0.7977.167',
    'node_version': 'v24.22.0',
    'chromium_git': 'https://chromium.googlesource.com',
    'nodejs_git': 'https://github.com/nodejs',
}
deps = {
    'src': {'url': Var('chromium_git') + '/chromium/src.git@' + Var('chromium_version')},
    'src/third_party/electron_node': {'url': Var('nodejs_git') + '/node.git@' + Var('node_version')},
}
"""


def version_patch(before, after):
    return ("diff --git a/DEPS b/DEPS\n--- a/DEPS\n+++ b/DEPS\n"
            "@@ -2,3 +2,3 @@\n"
            "     'chromium_version': '152.0.7977.167',\n"
            f"-    'node_version': '{before}',\n"
            f"+    'node_version': '{after}',\n"
            "     'chromium_git': 'https://chromium.googlesource.com',\n")


class Preparation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="electron-source-test-")
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)
        self.source = self.work / "source"
        self.source.mkdir()
        self.destination = self.work / "prepared"
        self.patches = self.work / "patches"
        self.patches.mkdir()
        (self.patches / "patch-security").write_text(version_patch("v24.22.0", "v24.22.1"))
        self.git("init", "-q")
        (self.source / "DEPS").write_text(DEPS)
        self.commit()
        self.pin_patch = patch.object(preparer, "ELECTRON_REVISION", self.git("rev-parse", "HEAD"))
        self.pin_patch.start()
        self.addCleanup(self.pin_patch.stop)
        patches = patch.object(preparer, "PATCHES", ("patch-security",))
        patches.start()
        self.addCleanup(patches.stop)

    def git(self, *args, cwd=None):
        result = subprocess.run([str(options.git), "-C", str(cwd or self.source),
                                 "-c", "user.name=Source Test",
                                 "-c", "user.email=test@example.invalid", *args],
                                capture_output=True, text=True, check=True)
        return result.stdout.strip()

    def commit(self):
        self.git("add", "DEPS")
        self.git("commit", "-qm", "fixture")

    def prepare(self):
        return preparer.prepare(self.source, self.destination, options.git, "arm64", self.patches)

    def change_pinned_deps(self, text):
        (self.source / "DEPS").write_text(text)
        self.commit()
        preparer.ELECTRON_REVISION = self.git("rev-parse", "HEAD")

    def test_success_and_source_preservation(self):
        before = self.git("status", "--porcelain")
        electron = self.prepare()
        self.assertEqual((self.source / "DEPS").read_text(), DEPS)
        self.assertEqual(self.git("status", "--porcelain"), before)
        self.assertEqual((electron / "DEPS").read_text(), DEPS.replace("v24.22.0", "v24.22.1"))
        self.assertEqual(self.git("remote", "get-url", "origin", cwd=electron),
                         "https://github.com/electron/electron.git")
        config = ast.parse((self.destination / ".gclient").read_text())
        values = {node.targets[0].id: ast.literal_eval(node.value) for node in config.body}
        solution = values["solutions"][0]
        self.assertFalse(solution["managed"])
        self.assertEqual(solution["name"], "src/electron")
        self.assertEqual(solution["custom_vars"]["chromium_version"],
                         "dd78960ccd8a03a2fe1f629543d27783885b78e9")
        self.assertEqual(solution["custom_vars"]["node_version"],
                         "ce7aaf1cee78b8cf0ce17364260535c418d3ed26")
        self.assertFalse(solution["custom_vars"]["install_sysroot"])
        self.assertEqual(values["target_cpu"], ["arm64"])
        self.assertEqual(values["target_os"], ["linux"])

    def test_wrong_head(self):
        preparer.ELECTRON_REVISION = "0" * 40
        with self.assertRaisesRegex(ValueError, "HEAD"):
            self.prepare()
        self.assertFalse(self.destination.exists())

    def test_tracked_change(self):
        (self.source / "DEPS").write_text(DEPS + "# local change\n")
        with self.assertRaisesRegex(ValueError, "clean"):
            self.prepare()

    def test_untracked_change(self):
        (self.source / "local.txt").write_text("keep me")
        with self.assertRaisesRegex(ValueError, "clean"):
            self.prepare()

    def test_wrong_chromium_pin(self):
        self.change_pinned_deps(DEPS.replace("152.0.7977.167", "152.0.7977.82"))
        with self.assertRaisesRegex(ValueError, "chromium_version"):
            self.prepare()
        self.assertFalse(self.destination.exists())

    def test_already_patched_source(self):
        self.change_pinned_deps(DEPS.replace("v24.22.0", "v24.22.1"))
        with self.assertRaisesRegex(ValueError, "node_version"):
            self.prepare()

    def test_changed_url_cannot_bypass_pin(self):
        self.change_pinned_deps(DEPS.replace("/chromium/src.git@", "/other.git@"))
        with self.assertRaisesRegex(ValueError, "URL"):
            self.prepare()

    def test_deps_is_never_executed(self):
        self.change_pinned_deps(DEPS.replace("Var('chromium_git')", "dangerous()"))
        with self.assertRaisesRegex(ValueError, "URL expression"):
            self.prepare()

    def test_duplicate_assignment(self):
        self.change_pinned_deps(DEPS + "vars = {}\n")
        with self.assertRaisesRegex(ValueError, "exactly once"):
            self.prepare()

    def test_existing_destination_and_rerun_preserved(self):
        self.prepare()
        before = (self.destination / ".gclient").read_bytes()
        with self.assertRaisesRegex(ValueError, "already exists"):
            self.prepare()
        self.assertEqual((self.destination / ".gclient").read_bytes(), before)

    def test_nested_destination_refused(self):
        self.destination = self.source / "work"
        with self.assertRaisesRegex(ValueError, "outside source"):
            self.prepare()

    def test_missing_patch_before_mutation(self):
        (self.patches / "patch-security").unlink()
        with self.assertRaisesRegex(ValueError, "patch is missing"):
            self.prepare()
        self.assertFalse(self.destination.exists())

    def test_unlisted_patch_refused(self):
        (self.patches / "patch-extra").write_text(version_patch("v24.22.1", "v24.22.2"))
        with self.assertRaisesRegex(ValueError, "complete patch directory"):
            self.prepare()
        self.assertFalse(self.destination.exists())

    def test_duplicate_patch_refused(self):
        preparer.PATCHES = ("patch-security", "patch-security")
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.prepare()
        self.assertFalse(self.destination.exists())

    def test_patch_reject_retains_partial_work_without_config(self):
        (self.patches / "patch-security").write_text(version_patch("v0.0.0", "v24.22.1"))
        with self.assertRaisesRegex(ValueError, "apply failed"):
            self.prepare()
        self.assertTrue((self.destination / "src/electron/DEPS").is_file())
        self.assertFalse((self.destination / ".gclient").exists())
        self.assertEqual((self.source / "DEPS").read_text(), DEPS)

    def test_ordered_patch_chain(self):
        (self.patches / "patch-security").write_text(version_patch("v24.22.0", "intermediate"))
        (self.patches / "patch-next").write_text(version_patch("intermediate", "v24.22.1"))
        preparer.PATCHES = ("patch-security", "patch-next")
        self.prepare()
        self.destination = self.work / "reversed"
        preparer.PATCHES = ("patch-next", "patch-security")
        with self.assertRaisesRegex(ValueError, "apply failed"):
            self.prepare()
        self.assertFalse((self.destination / ".gclient").exists())

    def test_patched_pin_mismatch(self):
        (self.patches / "patch-security").write_text(version_patch("v24.22.0", "v25.0.0"))
        with self.assertRaisesRegex(ValueError, "node_version"):
            self.prepare()
        self.assertFalse((self.destination / ".gclient").exists())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--git", required=True, type=Path)
    parser.add_argument("--electron-source", type=Path,
                        help="also exercise the unmodified production pin and recipe patches")
    options = parser.parse_args()
    owner = Path(__file__).resolve().parents[1] / "electron44"
    spec = importlib.util.spec_from_file_location("prepare_sources", owner / "files/prepare-sources.py")
    preparer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(preparer)
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Preparation))
    if not result.wasSuccessful():
        raise SystemExit(1)
    if options.electron_source:
        with tempfile.TemporaryDirectory(prefix="electron-production-source-") as work:
            root = preparer.prepare(options.electron_source, Path(work) / "prepared", options.git,
                                    "arm64", owner / "patches")
            preparer.check_deps(root / "DEPS", "v24.22.1")
        print("PASS: production Electron pin and complete recipe-local patch series")
    print("Scope: DEPS input preparation only; no dependency sync, hooks, compilation or target runtime")
