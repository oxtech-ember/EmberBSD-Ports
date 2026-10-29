#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Exercise Meson test-copy RUNPATH fixup with real cross-linked ELF files."""
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

owner = Path(__file__).resolve().parents[1] / 'cross/prepare-mesa-package-tests.py'
spec = importlib.util.spec_from_file_location('mesa_package_rpath', owner)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
tools, sysroot = map(lambda s: Path(s).resolve(strict=True), sys.argv[1:])
cc = tools / 'bin/x86_64--netbsd-clang'
readelf = tools / 'bin/x86_64--netbsd-readelf'
build_rpath = str(sysroot / 'usr/pkg/lib')
allowed = ['/usr/pkg/lib', '/usr/lib']
with tempfile.TemporaryDirectory() as td:
    root = Path(td); source = root / 'case.c'; source.write_text('int test_symbol;\n')
    original = root / 'original'; copy = root / 'copy'; foreign = root / 'foreign'
    def link(path, rpath):
        subprocess.run([str(cc), '-shared', '-nostdlib', str(source), '-Wl,-rpath,' + rpath,
                        '-o', str(path)], check=True)
    link(original, '/usr/pkg/lib:' + build_rpath)
    before = m.digest(original); shutil.copy2(original, copy)
    m.normalize_test_rpath(copy, readelf, sysroot, '-Wl,-rpath,' + build_rpath, allowed, Path(sys.executable))
    dynamic = m.query(str(readelf), '-d', str(copy))
    assert '/usr/pkg/lib' in dynamic and build_rpath not in dynamic
    assert m.digest(original) == before
    link(foreign, '/usr/pkg/lib:/foreign/lib')
    try:
        m.normalize_test_rpath(foreign, readelf, sysroot, '-Wl,-rpath,' + build_rpath, allowed, Path(sys.executable))
    except ValueError as e:
        assert 'foreign ELF runtime path' in str(e)
    else:
        raise AssertionError('foreign path accepted')
    try:
        m.normalize_test_rpath(original, readelf, sysroot, '', allowed, Path(sys.executable))
    except ValueError as e:
        assert 'foreign ELF runtime path' in str(e)
    else:
        raise AssertionError('unrecorded sysroot path accepted')
print('PASS: copied ELF build path removed, target path preserved, foreign/unrecorded rejected')
