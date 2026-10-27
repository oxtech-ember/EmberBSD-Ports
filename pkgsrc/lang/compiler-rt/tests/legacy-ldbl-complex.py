#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Compile source/object diagnostics using the supplied sysroot headers."""
import argparse
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--clang', type=Path, required=True)
parser.add_argument('--nm', type=Path, required=True)
parser.add_argument('--sysroot', type=Path, required=True,
                    help='headers for source/object diagnostics, not ABI acceptance')
parser.add_argument('--work-dir', type=Path, required=True)
args = parser.parse_args()
builtins = args.source / 'compiler-rt/lib/builtins'
with tempfile.TemporaryDirectory(dir=args.work_dir) as temporary:
    for name in ('divxc3', 'mulxc3'):
        source = builtins / (name + '.c')
        for target, optin, expected in (
                ('aarch64--netbsd', False, False),
                ('aarch64--netbsd', True, True),
                ('x86_64--netbsd', False, True),
                ('x86_64--netbsd', True, True),
                ('armv7--netbsd', True, True)):
            output = Path(temporary) / (name + '.o')
            command = [str(args.clang), '--target=' + target,
                       '--sysroot=' + str(args.sysroot), '-std=gnu11',
                       '-I' + str(builtins), '-c', str(source), '-o', str(output)]
            if optin:
                command.insert(-4, '-DEMBERBSD_LEGACY_LDBL_COMPLEX_ABI')
            result = subprocess.run(command, capture_output=True, text=True)
            assert (result.returncode == 0) == expected, result.stderr
            if not expected:
                assert 'xf_float' in result.stderr, result.stderr
                continue
            symbols = subprocess.check_output([str(args.nm), '--defined-only', str(output)], text=True)
            assert '__' + name in symbols, symbols
print('legacy long-double complex source/object diagnostics: passed')
