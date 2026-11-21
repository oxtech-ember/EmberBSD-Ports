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
p.add_argument('--cross-makeconf', type=Path, help='also check a configured EmberBSD cross target')
a = p.parse_args()

def query(abi, variable, *, cross=False, makefile=None):
    config = [f'MAKECONF={a.cross_makeconf}'] if cross else [
        f'MAKECONF={a.makeconf}', 'EMBERBSD_DARWIN_BOOTSTRAP=yes',
        'EMBERBSD_DARWIN_TOOLCHAIN_ONLY=yes']
    command = [a.bmake, '-C', a.pkgsrc/'fonts/harfbuzz']
    if makefile is not None:
        command.extend(['-f', makefile])
    return subprocess.run([*command, *config, f'EMBERBSD_NATIVE_CXX_ABI_NAMESPACE={abi}',
        '-v', variable], check=True, text=True, stdout=subprocess.PIPE).stdout.strip()
assert query('__ember1', 'PKGNAME') == 'harfbuzz-15.2.0nb1'
assert query('__1', 'PKGNAME') == 'harfbuzz-15.2.0'
if a.cross_makeconf:
    assert query('__ember1', 'OPSYS', cross=True) == 'NetBSD'
    assert query('__ember1', 'USE_CROSS_COMPILE', cross=True) == 'yes'
    assert query('__ember1', 'PKGNAME', cross=True) == 'harfbuzz-15.2.0'
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
    def consumer(abi, *, cross=False):
        return query(abi, 'BUILDLINK_ABI_DEPENDS.harfbuzz', cross=cross, makefile=fixture)
    assert 'harfbuzz>=15.2.0nb1' in consumer('__ember1')
    assert 'harfbuzz>=15.2.0' in consumer('__1')
    assert 'harfbuzz>=15.2.0nb1' not in consumer('__1')
    if a.cross_makeconf:
        assert 'harfbuzz>=15.2.0nb1' not in consumer('__ember1', cross=True)
print('HarfBuzz native ABI metadata PASS')
