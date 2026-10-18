#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Compiler-produced DWP fixtures.
import os
from pathlib import Path
import shutil
import struct
import sys
sys.dont_write_bytecode = True
from llvm_host import checked_paths, load_sdk, query, log_run


def build(args):
    from emberbsd_sdk.process import capture
    if len(args) != 3:
        raise ValueError('Use GCC16_DRIVER SYSROOT NEW_WORK')
    cc, sysroot, work = args
    checked_paths(args)
    cxx = os.environ.get('CXX', cc.removesuffix('gcc') + 'g++')
    objcopy = os.environ.get('OBJCOPY', cc.removesuffix('gcc') + 'objcopy')
    if query([cc, '-dumpmachine']) != 'aarch64--netbsd' or query([cc, '-dumpfullversion']) != '16.2.0':
        raise ValueError('Common AArch64 GCC16 compiler required')
    os.mkdir(work)
    here = Path(__file__).resolve().parent
    crt = sysroot + '/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0/'
    for name in ('llvm-dwp-main.cpp', 'llvm-dwp-helper.cpp'):
        shutil.copyfile(here / name, Path(work, name))
    Path(work, 'compiler.txt').write_text(query([cxx, '--version']) + '\n')
    common = [cxx, '--sysroot=' + sysroot, '-B' + crt]
    with open(work + '/cases.tsv', 'w') as cases:
        for version in (4, 5):
            for widths in ('32-32', '64-64', '32-64', '64-32'):
                for types in ('plain', 'types'):
                    name = f'v{version}-w{widths}-{types}'
                    directory = Path(work, name)
                    directory.mkdir()
                    extra = ['-DTYPES', '-fdebug-types-section'] if types == 'types' else []
                    log_run(directory / 'main.log', common + ['-O0', '-gdwarf-' + str(version), '-gdwarf' + widths[:2], '-gsplit-dwarf', *extra, '-fno-omit-frame-pointer', '-c', '../llvm-dwp-main.cpp', '-o', 'main.o'], cwd=directory)
                    log_run(directory / 'helper.log', common + ['-O0', '-gdwarf-' + str(version), '-gdwarf' + widths[-2:], '-gsplit-dwarf', '-c', '../llvm-dwp-helper.cpp', '-o', 'helper.o'], cwd=directory)
                    log_run(directory / 'link.log', common + ['main.o', 'helper.o', '-o', 'program'], cwd=directory)
                    cases.write(f'{name}\t{version}\t{types}\n')
    malformed = Path(work, 'malformed')
    malformed.mkdir()
    source = work + '/v5-w64-64-plain/main.dwo'
    for name, section in [('offsets', '.debug_str_offsets.dwo'), ('info', '.debug_info.dwo'), ('strings', '.debug_str.dwo')]:
        capture([objcopy, '--dump-section', section + '=' + str(malformed / (name + '.bin')), source])
    offsets, info, strings = [(malformed / (p + '.bin')).read_bytes() for p in ('offsets', 'info', 'strings')]
    damaged = {'short-header': offsets[:8], 'short-entry': offsets[:-1], 'short-unit': info[:8], 'unterminated': strings[:-1]}
    for name, data, offset, value in [('long-table', offsets, 4, len(offsets) + 64), ('bad-string', offsets, 16, 2**64 - 1), ('long-unit', info, 4, 2**64 - 1), ('suffix-strings', offsets + struct.pack('<Q', 1), 4, len(offsets) + 8 - 12)]:
        data = bytearray(data)
        struct.pack_into('<Q', data, offset, value)
        damaged[name] = data
    for name, data in damaged.items():
        path = malformed / (name + '.bin')
        path.write_bytes(data)
        section = '.debug_info.dwo' if 'unit' in name else '.debug_str.dwo' if name == 'unterminated' else '.debug_str_offsets.dwo'
        capture([objcopy, '--update-section', section + '=' + str(path), source, str(malformed / (name + '.dwo'))])
    for width in (32, 64):
        for kind in ('max-strx', 'truncated-strx'):
            flags = (['-DDW64'] if width == 64 else []) + (['-DTRUNCATED'] if kind == 'truncated-strx' else [])
            capture([cc, '--sysroot=' + sysroot, *flags, '-c', str(here / 'llvm-dwp-malformed.S'), '-o', str(malformed / f'{kind}-w{width}.dwo')])
    print('Built 16 two-CU DWP fixtures, 11 malformed inputs and a string-suffix input.')


if __name__ == '__main__':
    try:
        _, args = load_sdk()
        build(args)
    except Exception as error:
        sys.exit(f'FAIL: {error}')
