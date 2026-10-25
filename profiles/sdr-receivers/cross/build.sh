#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; explicit-tool CMake build of the common AIS recipe.
set -eu
[ "$#" -eq 4 ] || { echo 'Usage: build.sh PATCHED_SOURCE SYSROOT TOOLCHAIN NEW_WORK' >&2; exit 2; }
: "${PY:?Select an absolute Python interpreter}"
exec "$PY" - "$@" "$(dirname "$0")/../../../pkgsrc/ham/ais-catcher" <<'PY'
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

source, sysroot, toolchain, work = map(Path, sys.argv[1:5])
recipe = Path(sys.argv[5]).resolve()
for directory in (source, sysroot, toolchain, work):
    if not directory.is_absolute() or any(c.isspace() for c in str(directory)):
        raise SystemExit('Absolute build paths without whitespace are required')
if work.exists():
    raise SystemExit('NEW_WORK already exists')
for directory in (source, sysroot, toolchain):
    if not directory.is_dir():
        raise SystemExit('Missing input directory: ' + str(directory))
tools = {role: Path(os.environ[role]) for role in ('CC', 'CXX', 'CMAKE', 'NINJA', 'PKG_CONFIG')}
for role, path in tools.items():
    if not path.is_absolute() or not os.access(path, os.X_OK):
        raise SystemExit('Select an absolute executable for ' + role)
triplets = []
versions = []
for role in ('CC', 'CXX'):
    if not tools[role].resolve().is_relative_to(toolchain.resolve()):
        raise SystemExit('Compiler is outside the selected toolchain')
    version = subprocess.check_output([str(tools[role]), '-dumpfullversion'], text=True).strip()
    if not version.startswith('16.'):
        raise SystemExit('GCC16 is required')
    versions.append(version)
    identity = subprocess.run([str(tools[role]), '-v'], capture_output=True, text=True, check=True)
    if 'Thread model: posix' not in identity.stderr:
        raise SystemExit('A POSIX-threaded application compiler is required')
    triplets.append(subprocess.check_output([str(tools[role]), '-dumpmachine'], text=True).strip())
if versions[0] != versions[1]:
    raise SystemExit('Matching C and C++ compiler versions are required')
if triplets[0] != triplets[1] or triplets[0] not in ('x86_64--netbsd', 'aarch64--netbsd'):
    raise SystemExit('Matching EmberBSD application target compilers are required')
triplet = triplets[0]
crt = sysroot / 'usr/pkg/gcc16/lib/gcc' / triplet / version
for path in (sysroot / 'usr/include/stdio.h', crt / 'crtbegin.o',
             sysroot / 'usr/pkg/gcc16/include/c++' / triplet,
             sysroot / 'usr/pkg/include/rtl-sdr.h',
             sysroot / 'usr/pkg/include/libusb-1.0/libusb.h'):
    if not path.exists():
        raise SystemExit('Missing target input: ' + str(path))
for role in ('ar', 'ranlib', 'readelf'):
    tools[role] = toolchain / 'bin' / (triplet + '-' + role)
    if not os.access(tools[role], os.X_OK):
        raise SystemExit('Missing target tool: ' + role)
work.mkdir()
record = {role: {'path': str(path.resolve()), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
          for role, path in tools.items()}
(work / 'tools.json').write_text(json.dumps(record, indent=2) + '\n')
(work / 'toolchain.cmake').write_text('\n'.join([
    'set(CMAKE_SYSTEM_NAME NetBSD)',
    'set(CMAKE_SYSTEM_PROCESSOR ' + ('x86_64' if triplet.startswith('x86_64') else 'aarch64') + ')',
    f'set(CMAKE_SYSROOT "{sysroot}")',
    f'set(CMAKE_C_COMPILER "{tools["CC"]}")', f'set(CMAKE_CXX_COMPILER "{tools["CXX"]}")',
    f'set(CMAKE_CXX_FLAGS_INIT "-nostdinc++ -isystem {sysroot}/usr/pkg/gcc16/include/c++ -isystem {sysroot}/usr/pkg/gcc16/include/c++/{triplet} -isystem {sysroot}/usr/pkg/gcc16/include/c++/backward")',
    f'set(CMAKE_AR "{tools["ar"]}")', f'set(CMAKE_RANLIB "{tools["ranlib"]}")',
    f'set(CMAKE_FIND_ROOT_PATH "{sysroot}")',
    'set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)',
    'set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)',
    'set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)',
    'set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)',
    f'set(CMAKE_EXE_LINKER_FLAGS_INIT "-B{crt}/ -L{sysroot}/usr/pkg/gcc16/lib -Wl,-rpath-link,{sysroot}/usr/pkg/lib -Wl,-rpath-link,{sysroot}/usr/lib -Wl,-rpath-link,{sysroot}/lib -Wl,-rpath,/usr/pkg/gcc16/lib -Wl,-rpath,/usr/pkg/lib -Wl,-z,relro")',
]) + '\n')
env = dict(os.environ, PKG_CONFIG_SYSROOT_DIR=str(sysroot),
           PKG_CONFIG_LIBDIR=str(sysroot / 'usr/pkg/lib/pkgconfig'), PKG_CONFIG_PATH='')
commands = [
    [str(tools['CMAKE']), '-S', str(source), '-B', str(work / 'build'), '-G', 'Ninja',
     '-C', str(recipe / 'files/receiver.cmake'),
     '-DCMAKE_TOOLCHAIN_FILE=' + str(work / 'toolchain.cmake'),
     '-DCMAKE_MAKE_PROGRAM=' + str(tools['NINJA']),
     '-DPKG_CONFIG_EXECUTABLE=' + str(tools['PKG_CONFIG']),
     '-DCMAKE_INSTALL_PREFIX=/usr/pkg', '-DCMAKE_BUILD_WITH_INSTALL_RPATH=ON',
     '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON'],
    [str(tools['CMAKE']), '--build', str(work / 'build'), '--parallel', os.environ.get('JOBS', '2')],
    [str(tools['CMAKE']), '--install', str(work / 'build')],
]
for name, command in zip(('configure', 'build', 'install'), commands):
    with (work / (name + '.log')).open('wb') as log:
        subprocess.run(command, env=dict(env, DESTDIR=str(work / 'stage')),
                       stdout=log, stderr=subprocess.STDOUT, check=True)
doc = work / 'stage/usr/pkg/share/doc/ais-catcher'
doc.mkdir(parents=True)
(doc / 'LICENSE').write_bytes((source / 'LICENSE').read_bytes())
binary = work / 'stage/usr/pkg/bin/AIS-catcher'
header = binary.read_bytes()[:20]
if header[:5] != b'\x7fELF\x02' or int.from_bytes(header[18:20], 'little') != (62 if triplet.startswith('x86_64') else 183):
    raise SystemExit('Output does not match selected ELF64 target')
with (work / 'elf.txt').open('wb') as log:
    subprocess.run([str(tools['readelf']), '-h', '-l', '-d', str(binary)], stdout=log, check=True)
dynamic = subprocess.check_output([str(tools['readelf']), '-d', str(binary)], text=True)
if any(('RPATH' in line or 'RUNPATH' in line or 'NEEDED' in line) and any(str(root) in line for root in (sysroot, work, toolchain)) for line in dynamic.splitlines()):
    raise SystemExit('Build-host path leaked into ELF dependencies')
print('Staged AIS receiver: ' + str(binary))
print('Package registration, target execution and RF acceptance remain separate.')
PY
