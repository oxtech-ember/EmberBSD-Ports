#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Install the Rust sanitizer runtimes for the package's Darwin target."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

prefix = Path(sys.argv[1])
target, lipo = sys.argv[2:]
arch = {"aarch64-apple-darwin": "arm64", "x86_64-apple-darwin": "x86_64"}[target]
for libdir in (prefix / "lib", prefix / "lib/rustlib" / target / "lib"):
    for library in sorted(libdir.glob("librustc*_rt.*.dylib")):
        if library.is_symlink():
            continue
        arches = subprocess.check_output([lipo, "-archs", library], text=True).split()
        if arches == [arch]:
            continue
        with tempfile.TemporaryDirectory(dir=libdir) as work:
            selected = Path(work) / library.name
            subprocess.run([lipo, library, "-thin", arch, "-output", selected], check=True)
            shutil.copymode(library, selected)
            selected.replace(library)
