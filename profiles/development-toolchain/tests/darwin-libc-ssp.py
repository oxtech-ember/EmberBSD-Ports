#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Check that Darwin GCC16 uses the libSystem stack protector.

GCC defines TARGET_LIBC_PROVIDES_SSP only when configure finds that libc has
__stack_chk_fail. An explicit --enable-libssp skips that check and records
"no", so the driver adds -lssp_nonshared -lssp to every -fstack-protector
link. Programs then load libssp.0.dylib from the GCC16 prefix. The build
shell is one of them, and it fails under dyld when a GCC16 update removes the
old package. The Darwin recipe must pass --disable-libssp. The recipe check
needs no compiler:

  python3 -B darwin-libc-ssp.py --recipe-only

The Mach-O check links a -fstack-protector-all program with an installed
GCC16 driver. It needs a stack protector call and libSystem only:

  python3 -B darwin-libc-ssp.py --gcc GCC16_PREFIX/bin/gcc --work NEW_WORK
"""

import argparse
import os
from pathlib import Path
import struct
import subprocess
import sys

sys.dont_write_bytecode = True
RECIPE = Path(__file__).resolve().parents[1] / 'patches/gcc-darwin-host.patch'
LIBSYSTEM = '/usr/lib/libSystem.B.dylib'
PROGRAM = r'''#include <string.h>
int main(int argc, char **argv) {
    char buffer[64];
    strncpy(buffer, argv[argc - 1], sizeof buffer - 1);
    buffer[sizeof buffer - 1] = 0;
    return buffer[0] == 0;
}
'''
# LC_LOAD_DYLIB, LC_LOAD_WEAK_DYLIB, LC_REEXPORT_DYLIB, LC_LAZY_LOAD_DYLIB,
# LC_LOAD_UPWARD_DYLIB.
DYLIB_COMMANDS = {0xc, 0x80000018, 0x8000001f, 0x20, 0x80000023}
LC_RPATH = 0x8000001c
LC_SYMTAB = 0x2


def recipe_libssp_arguments():
    """Return the Darwin branch lines of the lang/gcc16/Makefile SSP choice."""
    lines = RECIPE.read_text().splitlines()
    start = lines.index('+++ b/lang/gcc16/Makefile')
    end = next(i for i in range(start + 1, len(lines)) if lines[i].startswith('--- a/'))
    body = [line[1:] for line in lines[start + 1:end] if line[:1] in (' ', '+')]
    assert '.elif ${OPSYS} == "Darwin"' in body, 'no Darwin branch in the libssp choice'
    branch = body.index('.elif ${OPSYS} == "Darwin"')
    stop = next(i for i in range(branch + 1, len(body)) if body[i].startswith('.'))
    assert body[stop] == '.else' and body[stop + 1] == 'CONFIGURE_ARGS+=\t--enable-libssp', \
        'the Darwin branch must precede the common --enable-libssp branch'
    words = [line for line in body[branch + 1:stop] if not line.startswith('#')]
    assert words == ['CONFIGURE_ARGS+=\t--disable-libssp'], words
    assert 'gcc_cv_libc_provides_ssp' not in RECIPE.read_text(), 'use the configure option'
    return words


def mach_o_load_commands(path):
    """Return dylibs, rpaths and undefined symbols of a 64-bit Mach-O file."""
    data = Path(path).read_bytes()
    magic, _, _, filetype, ncmds = struct.unpack_from('<5I', data)
    assert magic == 0xfeedfacf, '%s: not a thin 64-bit Mach-O file' % path
    offset, dylibs, rpaths, undefined = 32, [], [], set()
    for _ in range(ncmds):
        cmd, size = struct.unpack_from('<2I', data, offset)
        if cmd in DYLIB_COMMANDS or cmd == LC_RPATH:
            name = struct.unpack_from('<I', data, offset + 8)[0]
            text = data[offset + name:offset + size].split(b'\0', 1)[0].decode()
            (rpaths if cmd == LC_RPATH else dylibs).append(text)
        elif cmd == LC_SYMTAB:
            symoff, nsyms, stroff, _ = struct.unpack_from('<4I', data, offset + 8)
            for i in range(nsyms):
                strx, ntype = struct.unpack_from('<IB', data, symoff + 16 * i)
                if ntype & 0x0e == 0 and ntype & 0x01:
                    undefined.add(data[stroff + strx:].split(b'\0', 1)[0].decode())
        offset += size
    return {'filetype': filetype, 'dylibs': dylibs, 'rpaths': rpaths, 'undefined': undefined}


def link(gcc, work):
    source = work / 'ssp.c'
    source.write_text(PROGRAM)
    out = work / 'ssp'
    subprocess.run([str(gcc), '-O0', '-fstack-protector-all', str(source), '-o', str(out)],
                   check=True, cwd=work, env={'PATH': '/usr/bin:/bin', 'LC_ALL': 'C'})
    subprocess.run([str(out), 'x'], check=True)
    return out


def check(program):
    info = mach_o_load_commands(program)
    print('dylibs:', info['dylibs'])
    assert '___stack_chk_fail' in info['undefined'], 'the program has no stack protector call'
    assert info['dylibs'] == [LIBSYSTEM], 'the stack protector link loads more than libSystem'
    print('PASS: -fstack-protector-all links libSystem only')


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv == ['--recipe-only']:
        print('Darwin libssp arguments:', recipe_libssp_arguments())
        return
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--gcc', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    args = parser.parse_args(argv)
    for path in (args.gcc, args.work):
        assert path.is_absolute(), path
    assert os.uname().sysname == 'Darwin', 'needs a Mach-O link'
    recipe_libssp_arguments()
    args.work.mkdir()
    check(link(args.gcc, args.work))


if __name__ == '__main__':
    main()
