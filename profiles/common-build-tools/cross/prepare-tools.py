#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Compose existing host tools without rebuilding.
import os
from pathlib import Path
import sys
sys.dont_write_bytecode = True
from llvm_host import checked_paths, load_sdk, query


def prepare(args):
    profile = Path(__file__).resolve().parents[2] / 'development-toolchain'
    sys.path[:0] = [str(profile), str(profile / 'cross')]
    from target_options import parse
    from host import TARGETS
    target, mode, args = parse(args)
    if len(args) != 3:
        raise ValueError('Use [--target aarch64|amd64] GCC16_PREFIX NETBSD_TOOLDIR NEW_TOOLDIR')
    compiler, os_tools, output = args
    checked_paths(args)
    if os.path.lexists(output):
        raise ValueError('Output already exists')
    triplet = TARGETS[target][0]
    gcc = compiler + '/bin/' + triplet + '-gcc'
    if query([gcc, '-dumpmachine']) != triplet or query([gcc, '-dumpfullversion']) != '16.2.0':
        raise ValueError('Matching GCC16.2.0 target compiler required')
    tools = {name: compiler + '/bin/' + triplet + '-' + name for name in ('gcc', 'g++', 'cpp', 'gcc-ar', 'gcc-nm', 'gcc-ranlib', 'ar', 'as', 'ld', 'nm', 'objcopy', 'objdump', 'ranlib', 'readelf', 'strip')}
    tools['install'] = os_tools + '/bin/' + triplet + '-install'
    if not all(os.access(path, os.X_OK) for path in tools.values()):
        raise ValueError('Missing cross tool or NetBSD host install utility')
    Path(output, 'bin').mkdir(parents=True)
    for name, path in tools.items():
        Path(output, 'bin', triplet + '-' + name).symlink_to(path)
    print('Prepared GCC16 cross tools with the NetBSD host install utility.')


if __name__ == '__main__':
    try:
        _, args = load_sdk()
        prepare(args)
    except Exception as error:
        sys.exit(f'FAIL: {error}')
