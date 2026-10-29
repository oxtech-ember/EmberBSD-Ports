#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Query both ABI modes for installed Abseil C++ consumers."""
import argparse
import subprocess
from pathlib import Path
p = argparse.ArgumentParser()
for name in ('pkgsrc', 'bmake', 'makeconf'):
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
def query(recipe, abi, variable, *extra):
    return subprocess.run([str(a.bmake), '-C', str(a.pkgsrc / 'devel' / recipe),
                           f'MAKECONF={a.makeconf}', 'EMBERBSD_DARWIN_BOOTSTRAP=yes',
                           'EMBERBSD_DARWIN_TOOLCHAIN_ONLY=yes',
                           f'EMBERBSD_NATIVE_CXX_ABI_NAMESPACE={abi}', *extra,
                           '-v', variable], capture_output=True, text=True, check=True).stdout.strip()
for name, new, old in (('re2', 're2-20251105nb4', 're2-20251105nb3'),
                       ('effcee', 'effcee-1.2026.0nb3', 'effcee-1.2026.0nb2')):
    assert query(name, '__ember1', 'PKGNAME') == new
    assert query(name, '__1', 'PKGNAME') == old
    assert query(name, '__ember1', 'PKGNAME', 'OPSYS=NetBSD') == old
    deps = query(name, '__ember1', 'DEPENDS')
    assert 'libcxx>=23.1.4nb1:' in deps and 'abseil>=20260817.0nb4:' in deps
    assert 'EMBERBSD_NATIVE_CXX_ABI_NAMESPACE' in query(name, '__ember1', 'BUILD_DEFS')
    if name == 'effcee':
        assert 're2>=20251105nb4:' in deps
print('Abseil native consumer ABI metadata PASS')
