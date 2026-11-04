#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check Qt's native recipe argument and CMake's actual Mach-O install behavior."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser()
for name in ('pkgsrc', 'makeconf', 'bmake', 'prefix', 'macos-sdk'):
    parser.add_argument('--' + name, type=Path, required=True)
args = parser.parse_args()
prefix = args.prefix.resolve()
bin = prefix / 'bin'
args_line = subprocess.run([str(args.bmake), '-C', str(args.pkgsrc / 'x11/qt6-qtbase'),
    'MAKECONF=' + str(args.makeconf), 'PREFIX=' + str(prefix),
    '-V', '${CMAKE_CONFIGURE_ARGS}'],
    check=True, capture_output=True, text=True, timeout=45).stdout
selected = '-DCMAKE_INSTALL_RPATH:STRING=' + str(prefix / 'lib')
assert selected in args_line.split(), args_line
with tempfile.TemporaryDirectory(prefix='qt-install-rpath-') as temporary:
    root = Path(temporary)
    source, build, dest = root / 'source', root / 'build', root / 'dest'
    source.mkdir()
    (source / 'probe.c').write_text('int probe(void) { return 42; }\n')
    (source / 'CMakeLists.txt').write_text('''cmake_minimum_required(VERSION 3.20)
project(rpath C)
add_library(probe SHARED probe.c)
set_target_properties(probe PROPERTIES BUILD_RPATH "@LIB@" INSTALL_NAME_DIR "@PREFIX@/qt6/lib")
install(TARGETS probe LIBRARY DESTINATION lib)
'''.replace('@LIB@', str(prefix / 'lib')).replace('@PREFIX@', str(prefix)))
    env = dict(os.environ, PATH=str(bin) + ':' + str(prefix / 'gnu/bin'))
    cmake = str(bin / 'cmake')
    def run(*command, **kw):
        return subprocess.run(command, env=env, check=True, capture_output=True, text=True, **kw)
    run(cmake, '-S', str(source), '-B', str(build), '-G', 'Ninja',
        '-DCMAKE_MAKE_PROGRAM=' + str(bin / 'ninja'), '-DCMAKE_C_COMPILER=' + str(bin / 'clang'),
        '-DCMAKE_C_FLAGS=-fuse-ld=lld', '-DCMAKE_OSX_SYSROOT=' + str(args.macos_sdk),
        '-DCMAKE_OSX_DEPLOYMENT_TARGET=14.4',
        '-DCMAKE_INSTALL_NAME_TOOL=' + str(bin / 'llvm-install-name-tool'),
        '-DCMAKE_INSTALL_PREFIX=' + str(dest))
    run(cmake, '--build', str(build))
    obj = build / 'CMakeFiles/probe.dir/probe.c.o'
    stamp = (obj.stat().st_ino, obj.stat().st_mtime_ns)
    run(cmake, '--install', str(build))
    def paths(path):
        return run(str(bin / 'llvm-otool'), '-l', str(path)).stdout
    assert str(prefix / 'lib') in paths(build / 'libprobe.dylib')
    assert str(prefix / 'lib') not in paths(dest / 'lib/libprobe.dylib')
    run(cmake, '-S', str(source), '-B', str(build), selected)
    run(cmake, '--build', str(build))
    assert (obj.stat().st_ino, obj.stat().st_mtime_ns) == stamp
    second = root / 'second'
    env['DESTDIR'] = str(second)
    run(cmake, '--install', str(build))
    assert str(prefix / 'lib') in paths(second / str(dest).lstrip('/') / 'lib/libprobe.dylib')
    print('PASS: CMake retains selected install RPATH without recompiling')
