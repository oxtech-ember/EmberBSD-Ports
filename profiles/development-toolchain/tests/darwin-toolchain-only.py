#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Query real Clang metadata with full and prepared-prefix policies."""
import argparse
import subprocess
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--pkgsrc', type=Path, required=True)
p.add_argument('--bmake', type=Path, required=True)
p.add_argument('--makeconf', type=Path, required=True)
p.add_argument('--cxx', required=True)
a = p.parse_args()
base = [str(a.bmake), '-C', str(a.pkgsrc / 'lang/clang'),
        f'MAKECONF={a.makeconf}', 'EMBERBSD_DARWIN_BOOTSTRAP=yes']
def query(mode, var):
    result = subprocess.run(base + [f'EMBERBSD_DARWIN_TOOLCHAIN_ONLY={mode}', '-v', var],
                            text=True, capture_output=True, check=True)
    return result.stdout.strip()
full = query('no', 'BOOTSTRAP_DEPENDS')
limited = query('yes', 'BOOTSTRAP_DEPENDS')
for name in ('devel/rpcsvc-proto', 'x11/qt6-qtbase', 'devel/qt6-qttools'):
    assert '../../' + name in full
    assert '../../' + name not in limited
for mode in ('no', 'yes'):
    assert query(mode, 'PKG_CXX') == a.cxx
    deps = query(mode, 'DEPENDS')
    assert '../../lang/llvm' in deps and '../../devel/lld' in deps
bad = subprocess.run(base + ['EMBERBSD_DARWIN_TOOLCHAIN_ONLY=invalid', '-v', 'PKG_CXX'],
                     text=True, capture_output=True)
assert bad.returncode and 'EMBERBSD_DARWIN_TOOLCHAIN_ONLY must be yes or no' in bad.stderr
print('Full and toolchain-only Clang metadata and native CXX routing PASS')
