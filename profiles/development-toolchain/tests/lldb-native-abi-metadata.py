#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check real pkgsrc LLDB metadata for native Darwin C++ ABI selection."""
import argparse
import subprocess
from pathlib import Path
p = argparse.ArgumentParser()
for arg in ('pkgsrc', 'bmake', 'makeconf'):
    p.add_argument('--' + arg, type=Path, required=True)
a = p.parse_args()
base = [str(a.bmake), '-C', str(a.pkgsrc / 'devel/lldb'), f'MAKECONF={a.makeconf}',
        'EMBERBSD_DARWIN_BOOTSTRAP=yes', 'EMBERBSD_DARWIN_TOOLCHAIN_ONLY=yes']
def query(abi, key):
    return subprocess.run(base + [f'EMBERBSD_NATIVE_CXX_ABI_NAMESPACE={abi}', '-v', key],
                          check=True, text=True, capture_output=True).stdout.strip()
assert query('__ember1', 'PKGNAME') == 'lldb-23.1.6nb1'
deps = query('__ember1', 'DEPENDS')
for edge in ('libcxx>=23.1.6:', 'llvm>=23.1.6nb1:', 'clang>=23.1.6nb1:'):
    assert edge in deps
assert 'EMBERBSD_NATIVE_CXX_ABI_NAMESPACE' in query('__ember1', 'BUILD_DEFS')
assert query('__1', 'PKGNAME') == 'lldb-23.1.6'
assert 'libcxx>=23.1.6:' not in query('__1', 'DEPENDS')
other = subprocess.run(base + ['EMBERBSD_NATIVE_CXX_ABI_NAMESPACE=__ember1',
                              'OPSYS=NetBSD', '-v', 'PKGNAME'],
                       check=True, text=True, capture_output=True).stdout.strip()
assert other == 'lldb-23.1.6'
print('Native LLDB ABI metadata PASS')
