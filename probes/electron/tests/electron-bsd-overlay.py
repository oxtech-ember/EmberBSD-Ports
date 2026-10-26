#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Exercise the BSD source audit with real Git/patch and bounded tiny inputs."""

import argparse
import difflib
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch


def delta(old, new, name):
    return "".join(difflib.unified_diff(old.splitlines(keepends=True), new.splitlines(keepends=True),
                                      fromfile=name + ".orig", tofile=name))


class OverlayAudit(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="electron-bsd-overlay-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.workspace = self.root / "workspace"
        self.src = self.workspace / "src"
        self.src.mkdir(parents=True)
        (self.src / "alpha.cc").write_text("Electron upstream\n")
        (self.src / "obsolete.cc").write_text("disabled dialog\n")
        self.base = self.repository(self.src)
        node = self.src / "third_party/electron_node"
        node.mkdir(parents=True)
        (node / "node.cc").write_text("Node\n")
        node_pin = self.repository(node)
        self.pkgsrc = self.root / "pkgsrc"
        self.recipe = self.pkgsrc / "www/chromium"
        (self.recipe / "patches").mkdir(parents=True)
        patches = {
            "patch-alpha": delta("Chromium upstream\n", "BSD support\n", "alpha.cc"),
            "patch-new": delta("", "new BSD source\n", "new.cc"),
            "patch-obsolete": delta("enabled dialog\n", "BSD dialog\n", "obsolete.cc"),
            "patch-tools": delta("upstream tool\n", "BSD host tool\n", "tools/gn/host.cc"),
        }
        for name, content in patches.items():
            (self.recipe / "patches" / name).write_text(content)
        (self.recipe / "distinfo").write_text("".join(
            f"SHA1 ({name}) = {hashlib.sha1(content.encode()).hexdigest()}\n"
            for name, content in patches.items()))
        baseline_pin = self.repository(self.pkgsrc)
        self.data = self.root / "recipe-data"
        self.data.mkdir()
        adapted = delta("Electron upstream\n", "BSD support\n", "alpha.cc")
        self.adaptation = "".join(difflib.unified_diff(
            patches["patch-alpha"].splitlines(keepends=True), adapted.splitlines(keepends=True),
            fromfile="a/patch-alpha", tofile="b/patch-alpha"))
        (self.data / "adaptations.patch").write_text(self.adaptation)
        self.archive = self.root / "overlay.tar.gz"
        self.archive.write_bytes(self.tar([("nb/LICENSE", b"fixture license\n", None)]))
        self.manifest = {
            "pkgsrc_revision": baseline_pin, "patch_count": 4, "archive_root": "nb",
            "archive_sha512": hashlib.sha512(self.archive.read_bytes()).hexdigest(),
            "adapted": [{"patch": "patch-alpha", "target": "alpha.cc",
                         "source_sha256": hashlib.sha256(b"Electron upstream\n").hexdigest()}],
            "superseded": {"patch-obsolete": {"target": "obsolete.cc", "reason": "disabled upstream",
                          "source_sha256": hashlib.sha256(b"disabled dialog\n").hexdigest()}},
            "external_host_tools": {"patch-tools": {"provider": "shared GN", "reason": "external host input"}},
        }
        self.write_manifest()
        inputs = self.workspace / "source-inputs"
        inputs.mkdir()
        actual = {"src": {"url": "https://example.invalid/chromium.git", "rev": self.base},
                  "src/third_party/electron_node": {"url": "https://example.invalid/node.git", "rev": node_pin}}
        for name in ("git-revisions.json", "declared-dependencies.json"):
            (inputs / name).write_text(json.dumps(actual))
        (inputs / "upstream-patches.json").write_text(json.dumps({
            "applied": {"src": {"base": self.base, "patched": self.base}}, "unselected": []}))
        pins = patch.multiple(helper.upstream.source, CHROMIUM_REVISION=self.base, NODE_REVISION=node_pin)
        pins.start()
        self.addCleanup(pins.stop)
        data = patch.object(helper, "DATA", self.data)
        data.start()
        self.addCleanup(data.stop)
        self.destination = self.root / "audit"

    def write_manifest(self):
        (self.data / "manifest.json").write_text(json.dumps(self.manifest))

    def git(self, root, *args):
        result = subprocess.run([str(options.git), "-C", str(root), "-c", "user.name=Fixture",
                                 "-c", "user.email=fixture@example.invalid", *args],
                                capture_output=True, text=True, check=True)
        return result.stdout.strip()

    def repository(self, root):
        self.git(root, "init", "-q")
        self.git(root, "add", ".")
        self.git(root, "commit", "-qm", "fixture")
        return self.git(root, "rev-parse", "HEAD")

    def audit(self):
        return helper.audit(self.workspace, self.pkgsrc, self.archive, self.destination,
                            options.git, options.patch)

    def tar(self, rows):
        raw = io.BytesIO()
        with tarfile.open(fileobj=raw, mode="w") as tar:
            for name, data, kind in rows:
                entry = tarfile.TarInfo(name)
                if kind:
                    entry.type = kind
                    entry.linkname = "target"
                else:
                    entry.size = len(data)
                tar.addfile(entry, io.BytesIO(data))
        return gzip.compress(raw.getvalue(), mtime=0)

    def archive_rows(self, rows):
        self.archive.write_bytes(self.tar(rows))
        self.manifest["archive_sha512"] = hashlib.sha512(self.archive.read_bytes()).hexdigest()
        return helper.overlay_files(self.archive, self.manifest)

    def test_ordered_real_git_and_patch_with_explicit_classification(self):
        result = self.audit()
        self.assertEqual([r["status"] for r in result["rows"]],
                         ["applied", "applied", "superseded", "external-host-tool"])
        self.assertEqual((self.destination / "files/alpha.cc").read_text(), "BSD support\n")
        self.assertEqual((self.destination / "files/new.cc").read_text(), "new BSD source\n")
        self.assertEqual((self.src / "alpha.cc").read_text(), "Electron upstream\n")
        self.assertFalse((self.src / "new.cc").exists())
        self.assertEqual(self.git(self.src, "rev-parse", "HEAD"), self.base)
        self.assertTrue((self.destination / "audit.json").is_file())

    def test_unadapted_patch_causally_fails(self):
        baseline = self.recipe / "patches/patch-alpha"
        with self.assertRaisesRegex(ValueError, "zero-fuzz patch failed"):
            helper.run_patch(options.patch, self.src, baseline, 0, self.root / "old.log")
        self.assertEqual((self.src / "alpha.cc").read_text(), "Electron upstream\n")

    def test_audit_reads_committed_sources_not_uncommitted_edits(self):
        (self.src / "alpha.cc").write_text("local changes must stay untouched\n")
        self.audit()
        self.assertEqual((self.destination / "files/alpha.cc").read_text(), "BSD support\n")
        self.assertEqual((self.src / "alpha.cc").read_text(), "local changes must stay untouched\n")

    def test_preimage_change_refused_without_completion(self):
        self.manifest["adapted"][0]["source_sha256"] = "0" * 64
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "source differs"):
            self.audit()
        self.assertFalse((self.destination / "audit.json").exists())

    def test_changed_head_refused(self):
        self.git(self.src, "commit", "--allow-empty", "-qm", "unexpected")
        with self.assertRaisesRegex(ValueError, "HEAD differs"):
            self.audit()

    def test_checksum_change_refused(self):
        (self.recipe / "distinfo").write_text((self.recipe / "distinfo").read_text().replace(
            hashlib.sha1((self.recipe / "patches/patch-alpha").read_bytes()).hexdigest(), "0" * 40))
        self.git(self.pkgsrc, "commit", "-qam", "invalid checksum")
        self.manifest["pkgsrc_revision"] = self.git(self.pkgsrc, "rev-parse", "HEAD")
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "patch checksum differs"):
            self.audit()
        self.assertFalse(self.destination.exists())

    def test_archive_checksum_change_refused(self):
        self.archive.write_bytes(self.archive.read_bytes() + b"extra")
        with self.assertRaisesRegex(ValueError, "archive checksum differs"):
            self.audit()
        self.assertFalse(self.destination.exists())

    def test_unclassified_missing_host_source_refused(self):
        self.manifest["external_host_tools"] = {}
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "unexpected existence"):
            self.audit()
        self.assertFalse((self.destination / "audit.json").exists())

    def test_undeclared_patch_adaptation_refused(self):
        self.manifest["adapted"] = []
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "declared patch set"):
            self.audit()

    def test_no_fuzz_fallback(self):
        target = self.root / "fuzz"
        target.mkdir()
        (target / "file").write_text("different context\nold\nend\n")
        filename = self.root / "fuzz.patch"
        filename.write_text(delta("context\nold\nend\n", "context\nnew\nend\n", "file"))
        with self.assertRaisesRegex(ValueError, "zero-fuzz patch failed"):
            helper.run_patch(options.patch, target, filename, 0, self.root / "fuzz.log")
        self.assertEqual((target / "file").read_text(), "different context\nold\nend\n")

    def test_archive_duplicate_traversal_and_symlink_refused(self):
        for rows in ([('nb/file', b'a', None), ('nb/file', b'b', None)],
                     [('nb/../escape', b'a', None)], [('nb/link', b'', tarfile.SYMTYPE)],
                     [('nb/Foo/a', b'a', None), ('nb/foo/b', b'b', None)]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                self.archive_rows(rows)

    def test_git_symlink_refused(self):
        (self.src / "link").symlink_to("alpha.cc")
        self.git(self.src, "add", "link")
        self.git(self.src, "commit", "-qm", "symlink")
        with self.assertRaisesRegex(ValueError, "regular source file"):
            helper.files_at(options.git, self.src, self.git(self.src, "rev-parse", "HEAD"), ["link"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--git", type=Path, required=True)
    parser.add_argument("--patch", type=Path, required=True)
    options, remaining = parser.parse_known_args()
    spec = importlib.util.spec_from_file_location(
        "bsd_overlay", Path(__file__).resolve().parents[1] / "electron44/files/audit-bsd-overlay.py")
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    unittest.main(argv=[__file__, *remaining])
