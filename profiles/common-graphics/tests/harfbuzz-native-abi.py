#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Query HarfBuzz native ABI and direct image-library metadata."""
import argparse
import subprocess
import tempfile
from pathlib import Path
p = argparse.ArgumentParser()
for name in ('pkgsrc', 'bmake', 'makeconf'):
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
def query(abi, variable, *extra):
    return subprocess.run([str(a.bmake), '-C', str(a.pkgsrc/'fonts/harfbuzz'),
        f'MAKECONF={a.makeconf}', 'EMBERBSD_DARWIN_BOOTSTRAP=yes',
        'EMBERBSD_DARWIN_TOOLCHAIN_ONLY=yes', f'EMBERBSD_NATIVE_CXX_ABI_NAMESPACE={abi}',
        *extra, '-v', variable], check=True, capture_output=True, text=True).stdout.strip()
assert query('__ember1', 'PKGNAME') == 'harfbuzz-15.0.0nb4'
assert query('__1', 'PKGNAME') == 'harfbuzz-15.0.0nb3'
assert query('__ember1', 'PKGNAME', 'OPSYS=NetBSD') == 'harfbuzz-15.0.0nb3'
deps = query('__ember1', 'DEPENDS')
assert 'libcxx>=23.1.4nb1:' in deps and 'png>=' in deps
assert 'EMBERBSD_NATIVE_CXX_ABI_NAMESPACE' in query('__ember1', 'BUILD_DEFS')
assert 'png>=' in query('__1', 'DEPENDS')
assert '-Dpng=enabled' in query('__1', 'MESON_ARGS')
with tempfile.TemporaryDirectory() as directory:
    fixture = Path(directory)/'consumer.mk'
    fixture.write_text('DISTNAME= fixture-1\nCATEGORIES= fonts\nCOMMENT= fixture\n'
        'LICENSE= mit\n.include "../../mk/bsd.prefs.mk"\n'
        '.include "../../fonts/harfbuzz/buildlink3.mk"\n.include "../../mk/bsd.pkg.mk"\n')
    def consumer(abi, *extra):
        return subprocess.run([str(a.bmake), '-C', str(a.pkgsrc/'fonts/harfbuzz'),
            '-f', str(fixture), f'MAKECONF={a.makeconf}', 'EMBERBSD_DARWIN_BOOTSTRAP=yes',
            'EMBERBSD_DARWIN_TOOLCHAIN_ONLY=yes', f'EMBERBSD_NATIVE_CXX_ABI_NAMESPACE={abi}',
            *extra, '-v', 'BUILDLINK_ABI_DEPENDS.harfbuzz'],
            check=True, capture_output=True, text=True).stdout
    assert 'harfbuzz>=15.0.0nb4' in consumer('__ember1')
    assert 'harfbuzz>=15.0.0nb3' in consumer('__1')
    assert 'harfbuzz>=15.0.0nb4' not in consumer('__1')
    assert 'harfbuzz>=15.0.0nb4' not in consumer('__ember1', 'OPSYS=NetBSD')
print('HarfBuzz native ABI metadata PASS')
