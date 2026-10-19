#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EmberBSD contributors
"""Host-only negative controls for ARMv7 build and installed-library gates."""

import argparse
import hashlib
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("cross_armv7", ROOT / "cross-armv7.py")
BUILD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD)


class Guards(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.compiler = self.root / "gcc"
        self.sysroot = self.root / "sysroot"
        self.work = self.root / "work"
        tools = self.compiler / "bin"
        tools.mkdir(parents=True)
        for name in ("ar", "ranlib", "nm", "readelf"):
            (tools / (BUILD.TARGET + "-" + name)).touch(mode=0o755)
        for name in ("usr/include/sys/param.h", "usr/lib/libc.so"):
            path = self.sysroot / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()

    def validate(self, outputs=None, macros="#define __GNUC__ 16\n"):
        with patch.object(BUILD, "output", side_effect=outputs or [BUILD.VERSION, BUILD.TARGET, "Machine: ARM\nFlags: hard-float ABI"]):
            with patch.object(subprocess, "check_output", return_value=macros):
                return BUILD.validate(self.compiler, self.sysroot, self.work)

    def test_valid_selection(self):
        self.assertEqual(self.validate(), self.compiler / "bin" / (BUILD.TARGET + "-gcc"))

    def test_existing_work(self):
        self.work.mkdir()
        with self.assertRaisesRegex(ValueError, "already exists"):
            self.validate()

    def test_dangling_work_link(self):
        self.work.symlink_to(self.root / "absent")
        with self.assertRaisesRegex(ValueError, "already exists"):
            self.validate()

    def test_old_gcc(self):
        with self.assertRaisesRegex(ValueError, "requires GCC"):
            self.validate(["12.5.0"])

    def test_wrong_target(self):
        with self.assertRaisesRegex(ValueError, "must target"):
            self.validate([BUILD.VERSION, "aarch64--netbsd"])

    def test_clang_compatibility_driver(self):
        with self.assertRaisesRegex(ValueError, "Clang"):
            self.validate(macros="#define __GNUC__ 16\n#define __clang__ 1\n")

    def test_missing_target_tool(self):
        (self.compiler / "bin" / (BUILD.TARGET + "-nm")).unlink()
        with self.assertRaisesRegex(ValueError, "Missing target tool"):
            self.validate()

    def test_missing_sysroot(self):
        (self.sysroot / "usr/lib/libc.so").unlink()
        with self.assertRaisesRegex(ValueError, "Missing EmberBSD sysroot"):
            self.validate()

    def test_wrong_sysroot_architecture(self):
        with self.assertRaisesRegex(ValueError, "ARM ELF"):
            self.validate([BUILD.VERSION, BUILD.TARGET, "Machine: AArch64"])

    def test_soft_float_sysroot(self):
        with self.assertRaisesRegex(ValueError, "hard-float"):
            self.validate([BUILD.VERSION, BUILD.TARGET, "Machine: ARM\nFlags: soft-float ABI"])

    def test_resolved_path_characters(self):
        odd = self.root / "path with spaces"
        odd.mkdir()
        linked = self.root / "link"
        linked.symlink_to(odd)
        self.work = linked / "build"
        with self.assertRaises(argparse.ArgumentTypeError):
            self.validate()

    def test_paths_and_jobs(self):
        for path in ("relative", "/tmp/with space", "/tmp/$path"):
            with self.subTest(path=path), self.assertRaises(argparse.ArgumentTypeError):
                BUILD.path_arg(path)
        for jobs in ("0", "-1", "x"):
            with self.subTest(jobs=jobs), self.assertRaises(argparse.ArgumentTypeError):
                BUILD.positive(jobs)

    def test_archive_digest_and_paths(self):
        for member in ("source/input", "../escape", "/absolute"):
            archive = self.root / "source.tar.gz"
            with tarfile.open(archive, "w:gz") as target:
                entry = tarfile.TarInfo(member)
                entry.size = 1
                target.addfile(entry, io.BytesIO(b"x"))
            expected = hashlib.sha256(archive.read_bytes()).hexdigest()
            if member == "source/input":
                BUILD.verify_archive(archive, expected)
            else:
                with self.assertRaisesRegex(ValueError, "Unsafe archive"):
                    BUILD.verify_archive(archive, expected)
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                BUILD.verify_archive(archive, "0" * 64)

    def test_library_provider_gate(self):
        tools = self.root / "bin"
        tools.mkdir()
        prefix = self.root / "prefix"
        tests = prefix / "libexec/ember-dsp"
        tests.mkdir(parents=True)
        for name in ("fftw-double", "fftw-float", "liquid-contract", "backend-selection"):
            (tests / name).write_text("#!/bin/sh\nexit 0\n")
            (tests / name).chmod(0o755)
        ldd = tools / "ldd"
        libraries = ("fftw3", "fftw3_threads", "fftw3f", "fftw3f_threads", "liquid")
        for provider, expected in ((prefix, 0), (self.root / "wrong", 1)):
            ldd.write_text("#!/bin/sh\n" + "".join(
                f"echo '{provider}/lib/lib{name}.so.1'\n" for name in libraries))
            ldd.chmod(0o755)
            result = subprocess.run(["sh", ROOT / "test-armv7.sh", prefix],
                env=os.environ | {"PATH": str(tools) + os.pathsep + os.environ["PATH"]},
                capture_output=True, text=True)
            self.assertEqual(result.returncode, expected, result.stderr)


if __name__ == "__main__":
    unittest.main()
