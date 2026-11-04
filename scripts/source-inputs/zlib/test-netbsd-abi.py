#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted), preserving NetBSD zlib ABI.
"""Compile the NetBSD libz.so.1 offset ABI and standalone source paths."""
import argparse
import itertools
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--cc', required=True)
parser.add_argument('--sysroot', required=True, type=Path)
parser.add_argument('--os-source', required=True, type=Path)
parser.add_argument('--zlib-source', required=True, type=Path)
args = parser.parse_args()
for target in ('i386--netbsd', 'x86_64--netbsd'):
    for have, large, file64 in itertools.product((False, True), repeat=3):
        flags = (['-DHAVE_UNISTD_H=1'] if have else []) + (['-D_LARGEFILE64_SOURCE=1'] if large else []) + (['-D_FILE_OFFSET_BITS=64'] if file64 else [])
        expected = 'off_t' if large else 'long'
        program = '''#include "zlib.h"
_Static_assert(__builtin_types_compatible_p(z_off_t, EXPECTED), "z_off_t ABI");
_Static_assert(__builtin_types_compatible_p(z_off64_t, z_off_t), "z_off64_t ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&gzseek), z_off_t (*)(gzFile, z_off_t, int)), "gzseek ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&gzoffset), z_off_t (*)(gzFile)), "gzoffset ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&adler32_combine), uLong (*)(uLong, uLong, z_off_t)), "adler ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&crc32_combine), uLong (*)(uLong, uLong, z_off_t)), "crc ABI");
int main(void) { return 0; }
'''.replace('EXPECTED', expected)
        cmd = [args.cc, '--target=' + target, '--sysroot=' + str(args.sysroot), '-I' + str(args.zlib_source), *flags, '-fsyntax-only', '-x', 'c', '-']
        result = subprocess.run(cmd, input=program, text=True, capture_output=True)
        if result.returncode:
            raise SystemExit(f'{target} {flags}: {result.stderr}')
for phase in ('_KERNEL', '_STANDALONE'):
    cmd = [args.cc, '--target=x86_64--netbsd', '--sysroot=' + str(args.sysroot), '-D' + phase,
           '-I' + str(args.zlib_source), '-I' + str(args.os_source / 'sys'), '-fsyntax-only',
           str(args.zlib_source / 'inftrees.c'), str(args.zlib_source / 'inflate.c')]
    result = subprocess.run(cmd, text=True, capture_output=True)
    if result.returncode:
        raise SystemExit(f'{phase}: {result.stderr}')
# H/PC uses Windows-hosted projects: select standalone compatibility without
# defining __NetBSD__ on that host.
hpc = [args.cc, '--target=x86_64--netbsd', '--sysroot=' + str(args.sysroot),
       '-U__NetBSD__', '-DZLIB_NETBSD_STANDALONE', '-D_STANDALONE',
       '-I' + str(args.zlib_source), '-I' + str(args.os_source / 'sys'),
       '-Werror', '-fsyntax-only']
result = subprocess.run(hpc + [str(args.zlib_source / 'inflate.c'),
                              str(args.zlib_source / 'inftrees.c')], text=True, capture_output=True)
if result.returncode:
    raise SystemExit('H/PC standalone source: ' + result.stderr)
program = '#include "zlib.h"\n_Static_assert(__builtin_types_compatible_p(z_off_t, long), "H/PC offset ABI");\n'
result = subprocess.run(hpc + ['-x', 'c', '-'], input=program, text=True, capture_output=True)
if result.returncode:
    raise SystemExit('H/PC standalone ABI: ' + result.stderr)
cmd = [args.cc, '--target=x86_64--netbsd', '--sysroot=' + str(args.sysroot),
       '-I' + str(args.zlib_source), '-Wcast-qual', '-Werror', '-fsyntax-only',
       *(str(args.zlib_source / name) for name in ('compress.c', 'deflate.c', 'uncompr.c', 'gzwrite.c'))]
result = subprocess.run(cmd, text=True, capture_output=True)
if result.returncode:
    raise SystemExit(f'NetBSD const-qualified build: {result.stderr}')
print('NetBSD zlib ABI and standalone compile matrix PASS')
