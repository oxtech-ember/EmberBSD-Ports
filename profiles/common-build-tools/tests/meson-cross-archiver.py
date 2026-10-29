#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check the archiver selection fragment under a synthetic cross guard."""
from pathlib import Path
import subprocess
import sys
import tempfile

if len(sys.argv) != 3:
    raise SystemExit('usage: meson-cross-archiver.py BMAKE MESON_BUILD_MK')
bmake, source = map(Path, sys.argv[1:])
if not all(p.is_absolute() and p.is_file() for p in (bmake, source)):
    raise SystemExit('use absolute existing bmake and Meson build.mk')
text = source.read_text()
start = text.index('# Select the host-executable SDK target archiver explicitly.')
end = text.index('MESON_CROSS_VARS+=', start)
fragment = text[start:end]
with tempfile.TemporaryDirectory() as temp:
    makefile = Path(temp) / 'fixture.mk'
    makefile.write_text('.if ${USE_CROSS_COMPILE:U:tl} == "yes"\n' + fragment + '.endif\n')
    def query(*assignments):
        return subprocess.check_output([str(bmake), '-r', '-f', str(makefile), *assignments,
                                        '-V', '${MESON_BINARIES}', '-V', '${MESON_BINARY.ar:U}'], text=True).splitlines()
    for family in ('clang', 'gcc'):
        actual = query('USE_CROSS_COMPILE=yes', 'EMBERBSD_CROSS_COMPILER_FAMILY=' + family,
                       'TOOLS_PATH.ar=/sdk/bin/selected-ar')
        if actual != ['ar', '/sdk/bin/selected-ar']:
            raise ValueError(f'{family}: {actual}')
        actual = query('USE_CROSS_COMPILE=yes', 'EMBERBSD_CROSS_COMPILER_FAMILY=' + family,
                       'TOOLS_PATH.ar=/sdk/bin/selected-ar', 'MESON_BINARY.ar=/caller/ar', 'MESON_BINARIES=ar')
        if actual != ['ar', '/caller/ar']:
            raise ValueError(f'{family} caller override: {actual}')
    for values in (('USE_CROSS_COMPILE=no', 'EMBERBSD_CROSS_COMPILER_FAMILY=clang'),
                   ('USE_CROSS_COMPILE=yes',)):
        actual = query(*values, 'TOOLS_PATH.ar=/sdk/bin/selected-ar')
        if actual != ['', '']:
            raise ValueError(f'unrelated route changed: {values} {actual}')
print('PASS: selection fragment for Clang/GCC, caller override, synthetic native and unrelated cross guards')
