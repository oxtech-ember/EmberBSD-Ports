#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Query SPIR-V translator package metadata for native ABI variants."""
import argparse
import subprocess
import tempfile
from pathlib import Path
p = argparse.ArgumentParser()
for name in ('pkgsrc', 'bmake', 'makeconf'):
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
def query(abi, variable, *extra):
    return subprocess.run([str(a.bmake), '-C', str(a.pkgsrc/'parallel/spirv-llvm-translator'),
        f'MAKECONF={a.makeconf}', 'EMBERBSD_DARWIN_BOOTSTRAP=yes',
        'EMBERBSD_DARWIN_TOOLCHAIN_ONLY=yes', f'EMBERBSD_NATIVE_CXX_ABI_NAMESPACE={abi}',
        *extra, '-v', variable], check=True, capture_output=True, text=True).stdout.strip()
assert query('__ember1', 'PKGNAME') == 'spirv-llvm-translator-23.1.2nb1'
assert query('__1', 'PKGNAME') == 'spirv-llvm-translator-23.1.2'
assert query('__ember1', 'PKGNAME', 'OPSYS=NetBSD') == 'spirv-llvm-translator-23.1.2'
deps = query('__ember1', 'DEPENDS')
assert 'libcxx>=23.1.4nb1:' in deps and 'llvm>=23.1.4nb5:' in deps
assert 'clang>=23.1.4nb11<23.2:' in query('__ember1', 'BUILD_DEPENDS')
assert 'EMBERBSD_NATIVE_CXX_ABI_NAMESPACE' in query('__ember1', 'BUILD_DEFS')
with tempfile.TemporaryDirectory() as directory:
    fixture = Path(directory)/'consumer.mk'
    fixture.write_text('DISTNAME= fixture-1\nCATEGORIES= parallel\nCOMMENT= fixture\n'
        'LICENSE= modified-bsd\n.include "../../mk/bsd.prefs.mk"\n'
        '.include "../../parallel/spirv-llvm-translator/buildlink3.mk"\n'
        '.include "../../mk/bsd.pkg.mk"\n')
    def consumer(abi, *extra):
        return subprocess.run([str(a.bmake), '-C', str(a.pkgsrc/'parallel/spirv-llvm-translator'),
            '-f', str(fixture), f'MAKECONF={a.makeconf}', 'EMBERBSD_DARWIN_BOOTSTRAP=yes',
            'EMBERBSD_DARWIN_TOOLCHAIN_ONLY=yes', f'EMBERBSD_NATIVE_CXX_ABI_NAMESPACE={abi}',
            *extra, '-v', 'BUILDLINK_ABI_DEPENDS.spirv-llvm-translator'],
            check=True, capture_output=True, text=True).stdout
    assert 'spirv-llvm-translator>=23.1.2nb1<23.2' in consumer('__ember1')
    assert 'spirv-llvm-translator>=23.1.2nb1<23.2' not in consumer('__1')
    assert 'spirv-llvm-translator>=23.1.2nb1<23.2' not in consumer('__ember1', 'OPSYS=NetBSD')
print('SPIR-V translator native ABI metadata PASS')
