#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Exercise OpenJPEG's internal copy failure paths using selected tools."""
import argparse
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--cc', required=True, type=Path)
p.add_argument('--source', required=True, type=Path)
p.add_argument('--config-dir', required=True, type=Path)
p.add_argument('--static-library', required=True, type=Path)
p.add_argument('--cc-arg', action='append', default=[])
p.add_argument('--compile-only', action='store_true')
p.add_argument('--strict-callbacks', action='store_true', help='check Clang function-pointer casts')
a = p.parse_args()
if not a.cc.is_absolute():
    p.error('--cc must be the absolute selected compiler')
with tempfile.TemporaryDirectory(prefix='openjpeg-ownership-') as tmp:
    root = Path(tmp)
    sources = Path(__file__).resolve().parent
    if a.strict_callbacks:
        subprocess.run([str(a.cc), *a.cc_arg, '-std=c99', '-Werror=cast-function-type-strict',
                        '-I' + str(a.source / 'src/lib/openjp2'), '-I' + str(a.config_dir),
                        '-fsyntax-only', str(a.source / 'src/lib/openjp2/openjpeg.c')], check=True)
    for name in ('deepcopy-test', 'image-copy-test'):
        binary = root / name
        cmd = [str(a.cc), *a.cc_arg, '-O1', '-I' + str(a.source / 'src/lib/openjp2'),
               '-I' + str(a.config_dir), str(sources / (name + '.c')),
               str(a.static_library), '-lm', '-lpthread', '-o', str(binary)]
        subprocess.run(cmd, check=True)
        if not a.compile_only:
            subprocess.run([str(binary)], check=True)
print('OpenJPEG PDFium copy/ownership ' + ('compile PASS' if a.compile_only else 'tests PASS'))
