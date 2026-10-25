#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; real CMake configuration regressions.
"""Check loader portability and mandatory RTL dependencies without target code.

The NetBSD platform fixture uses native GCC16 and an empty library root.
It tests CMake behavior only, not the NetBSD compiler, ABI or runtime.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('source', type=Path)
parser.add_argument('work', type=Path)
parser.add_argument('--baseline', action='store_true')
args = parser.parse_args()
args.work.mkdir()
empty = args.work / 'empty'
empty.mkdir()
roles = ['CMAKE', 'NINJA', 'CC', 'CXX', 'PKG_CONFIG']
tools = {role: os.environ[role] for role in roles}
for role, path in tools.items():
    if not Path(path).is_absolute() or not os.access(path, os.X_OK):
        raise SystemExit('Explicit executable required: ' + role)
for role in ('CC', 'CXX'):
    version = subprocess.check_output([tools[role], '-dumpfullversion'], text=True)
    if not version.startswith('16.'):
        raise SystemExit('Native GCC16 required')
common = [tools['CMAKE'], '-S', str(args.source), '-G', 'Ninja',
          '-DCMAKE_MAKE_PROGRAM=' + tools['NINJA'],
          '-DCMAKE_C_COMPILER=' + tools['CC'], '-DCMAKE_CXX_COMPILER=' + tools['CXX'],
          '-DPKG_CONFIG_EXECUTABLE=' + tools['PKG_CONFIG'],
          '-DCMAKE_FIND_ROOT_PATH=' + str(empty),
          '-DCMAKE_FIND_ROOT_PATH_MODE_LIBRARY=ONLY', '-DCMAKE_FIND_ROOT_PATH_MODE_INCLUDE=ONLY',
          '-DCMAKE_BUILD_WITH_INSTALL_RPATH=ON']
if os.environ.get('SDKROOT'):
    common.append('-DCMAKE_OSX_SYSROOT=' + os.environ['SDKROOT'])
for option in ['SOAPYSDR', 'AIRSPY', 'SDRPLAY', 'AIRSPYHF', 'HACKRF', 'HYDRASDR',
               'SOXR', 'ZLIB', 'SAMPLERATE', 'ZMQ', 'PSQL', 'SQLITE', 'OPENSSL',
               'NMEA2000', 'WEBVIEWER']:
    common.append('-D' + option + '=OFF')
env = dict(os.environ, PKG_CONFIG_LIBDIR=str(empty), PKG_CONFIG_PATH='')
for name, extra in [('netbsd-loader', ['-DCMAKE_SYSTEM_NAME=NetBSD',
                        '-DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY', '-DRTLSDR=OFF']),
                    ('missing-rtl', ['-DRTLSDR=ON'])]:
    result = subprocess.run(common + ['-B', str(args.work / name)] + extra,
                            env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (args.work / (name + '.log')).write_bytes(result.stdout)
    expected_success = (name == 'netbsd-loader') != args.baseline
    if (result.returncode == 0) != expected_success:
        raise SystemExit(f'{name}: unexpected exit {result.returncode}; see log')
    if name == 'netbsd-loader' and args.baseline and b'Could not find DL_LIBRARY' not in result.stdout:
        raise SystemExit('Baseline did not reproduce missing libdl')
    if name == 'missing-rtl' and not args.baseline and b'RTLSDR=ON requires' not in result.stdout:
        raise SystemExit('Missing RTL failed for an unrelated reason')
    print(f'PASS {name}: exit {result.returncode}; baseline={args.baseline}')

# Upstream replaced CMAKE_CXX_FLAGS and discarded caller toolchain/header flags.
result = subprocess.run(common + ['-B', str(args.work / 'compiler-flags'), '-DRTLSDR=OFF',
                        '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON',
                        '-DCMAKE_CXX_FLAGS=-DEMBER_FLAGS_SENTINEL=1'],
                        env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
(args.work / 'compiler-flags.log').write_bytes(result.stdout)
if result.returncode:
    raise SystemExit('Compiler-flag fixture configure failed')
commands = json.loads((args.work / 'compiler-flags/compile_commands.json').read_text())
preserved = all('-DEMBER_FLAGS_SENTINEL=1' in row['command'] for row in commands)
if preserved == args.baseline:
    raise SystemExit('Unexpected caller CXX flag preservation')
print(f'PASS compiler-flags: preserved={preserved}; baseline={args.baseline}')
