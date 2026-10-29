#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise fresh CMake link and install through a selected pkgsrc wrapper."""
import argparse
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
for name in ('bmake', 'pkgsrc', 'makeconf', 'cmake', 'ninja', 'cxx',
             'wrapper-config', 'otool', 'prefix', 'stage-root', 'python', 'link-launcher',
             'lock-root', 'link-context'):
    p.add_argument('--'+name, type=Path, required=True)
a = p.parse_args()
env = dict(os.environ)
env.pop('DYLD_LIBRARY_PATH', None)
env['CWRAPPERS_CONFIG_DIR'] = str(a.wrapper_config)
def run(command, env=env):
    result = subprocess.run([str(x) for x in command], env=env, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if result.returncode or 'duplicate -rpath' in result.stdout:
        raise RuntimeError(result.stdout[-4000:])
    return result.stdout

def query(extra):
    cmd = [a.bmake, '-C', a.pkgsrc/'lang/clang', 'MAKECONF='+str(a.makeconf),
           'EMBERBSD_DARWIN_BOOTSTRAP=yes', '_PKGSRC_BARRIER=yes', *extra,
           '-V', '${CMAKE_CONFIGURE_ARGS}', '-V', '${LDFLAGS}']
    args, flags = run(cmd).splitlines()
    values = [x.split('=', 1)[1] for x in shlex.split(args)
              if x.startswith('-DCMAKE_INSTALL_RPATH:STRING=')]
    assert len(values) == 1, values
    return values[0], flags

def paths(binary):
    lines = run([a.otool, '-l', binary]).splitlines()
    return [lines[i+2].strip().split()[1] for i, line in enumerate(lines) if 'cmd LC_RPATH' in line]

with tempfile.TemporaryDirectory(prefix='llvm-pkgsrc-stage-rpath-') as temporary:
    root = Path(temporary); src = root/'src'; src.mkdir()
    (src/'CMakeLists.txt').write_text('''cmake_minimum_required(VERSION 3.22)
project(rpath LANGUAGES CXX)
add_executable(probe main.cpp)
add_library(probe_lib SHARED lib.cpp)
install(TARGETS probe probe_lib RUNTIME DESTINATION bin LIBRARY DESTINATION lib)
''')
    (src/'main.cpp').write_text('int main() { return 0; }\n')
    (src/'lib.cpp').write_text('extern "C" int value() { return 1; }\n')
    for label, extra in (('normal', ()), ('empty', ('LDFLAGS=',))):
        rpath, flags = query(extra)
        build, dest = root/label, root/(label+'-dest')
        child = dict(env, LDFLAGS=flags)
        launcher = ';'.join(str(x) for x in (a.python, a.link_launcher, '--lock-root',
                                              a.lock_root, '--context', a.link_context, '--'))
        run([a.cmake, '-S', src, '-B', build, '-G', 'Ninja',
             '-DCMAKE_MAKE_PROGRAM='+str(a.ninja), '-DCMAKE_CXX_COMPILER='+str(a.cxx),
             '-DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY',
             '-DCMAKE_CXX_LINKER_LAUNCHER='+launcher,
             '-DCMAKE_INSTALL_PREFIX='+str(a.prefix),
             '-DCMAKE_BUILD_WITH_INSTALL_RPATH=ON', '-DCMAKE_INSTALL_RPATH='+rpath], child)
        run([a.ninja, '-C', build, '-j', '16'], child)
        run([a.cmake, '--install', build], dict(child, DESTDIR=str(dest)))
        for file in (dest/str(a.prefix/'bin/probe').lstrip('/'),
                     dest/str(a.prefix/'lib/libprobe_lib.dylib').lstrip('/')):
            actual = paths(file)
            assert actual == ['@loader_path/../lib', str(a.prefix/'lib')] or \
                actual == [str(a.prefix/'lib'), '@loader_path/../lib'], (label, actual)
            assert not any(str(a.stage_root) in value for value in actual)
print('PASS: fresh pkgsrc wrapper CMake RPATH, default and empty LDFLAGS')
