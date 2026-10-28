#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Compile the real V8 IEEE754 consumer with the selected LLVM libc source."""
import argparse
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
for name in ('source', 'v8', 'abseil', 'clang', 'macos-sdk'):
    p.add_argument('--' + name, type=Path, required=True)
p.add_argument('--deployment', required=True)
a = p.parse_args()
if not all(getattr(a, name).is_absolute() for name in ('source', 'v8', 'abseil', 'clang', 'macos_sdk')):
    p.error('select absolute paths')
with tempfile.TemporaryDirectory(prefix='v8 llvm-libc ') as temp:
    shim = Path(temp) / 'third_party/llvm-libc'; shim.mkdir(parents=True)
    (shim / 'src').symlink_to(a.source, target_is_directory=True)
    base = [str(a.clang), '-std=c++20', '-isysroot', str(a.macos_sdk),
            '-mmacosx-version-min=' + a.deployment, '-DLIBC_NAMESPACE=__llvm_libc_cr',
            '-I' + str(a.v8), '-I' + str(a.v8 / 'include'), '-I' + str(a.abseil)]
    source = str(a.v8 / 'src/base/ieee754.cc')
    good = subprocess.run([*base, '-I' + temp, '-I' + str(a.source), '-fsyntax-only', source],
                          text=True, capture_output=True)
    if good.returncode:
        raise RuntimeError('V8 consumer compile failed: ' + good.stderr)
    missing = subprocess.run([*base, '-fsyntax-only', source], text=True, capture_output=True)
    if missing.returncode == 0 or 'third_party/llvm-libc/src/shared/math.h' not in missing.stderr:
        raise RuntimeError('missing LLVM libc header negative control failed')
print('V8 IEEE754 common LLVM libc headers and missing-input control PASS')
