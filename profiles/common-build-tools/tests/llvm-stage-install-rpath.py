#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise upstream LLVM's RPATH helper on a staged Darwin consumer."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
for name in ('cmake', 'ninja', 'cc', 'cxx', 'ar', 'ranlib', 'install-name-tool',
             'otool', 'llvm-modules', 'prefix', 'stage-root', 'linker-adapter',
             'python', 'link-launcher', 'lock-root', 'link-context'):
    p.add_argument('--'+name, type=Path, required=True)
p.add_argument('--jobs', type=int, required=True)
a = p.parse_args()
if a.jobs < 1:
    p.error('--jobs must be positive')
env = dict(os.environ); env.pop('DYLD_LIBRARY_PATH', None)
def run(cmd, *, extra=None):
    child = dict(env, **(extra or {}))
    result = subprocess.run([str(x) for x in cmd], env=child, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError(result.stdout[-4000:])
    return result.stdout
def rpaths(path):
    lines = run([a.otool, '-l', path]).splitlines()
    return [lines[i+2].strip().split()[1] for i, line in enumerate(lines) if 'cmd LC_RPATH' in line]
with tempfile.TemporaryDirectory(prefix='llvm-stage-rpath-') as tmp:
    root = Path(tmp).resolve(); src = root/'src'; src.mkdir(); build = root/'build'; dest = root/'dest'
    (src/'CMakeLists.txt').write_text('''cmake_minimum_required(VERSION 3.22)
project(stage_rpath LANGUAGES C CXX)
list(APPEND CMAKE_MODULE_PATH "${LLVM_MODULE_SOURCE}")
include(AddLLVM)
add_executable(rpath_check main.cpp)
llvm_setup_rpath(rpath_check)
add_library(rpath_lib SHARED lib.cpp)
llvm_setup_rpath(rpath_lib)
install(TARGETS rpath_check rpath_lib RUNTIME DESTINATION bin LIBRARY DESTINATION lib)
''')
    (src/'main.cpp').write_text('int main() { return 0; }\n')
    (src/'lib.cpp').write_text('extern "C" int rpath_value() { return 42; }\n')
    staged_prefix = a.stage_root / str(a.prefix).lstrip('/')
    staged_lib = staged_prefix/'lib'; logical_lib = a.prefix/'lib'
    launcher = ';'.join((str(a.python), str(a.link_launcher), '--lock-root',
                         str(a.lock_root), '--context', str(a.link_context), '--'))
    cfg = [a.cmake, '-S', src, '-B', build, '-G', 'Ninja',
           '-DCMAKE_MAKE_PROGRAM='+str(a.ninja), '-DCMAKE_C_COMPILER='+str(a.cc),
           '-DCMAKE_CXX_COMPILER='+str(a.cxx), '-DCMAKE_AR='+str(a.ar),
           '-DCMAKE_RANLIB='+str(a.ranlib), '-DCMAKE_INSTALL_NAME_TOOL='+str(a.install_name_tool),
           '-DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY',
           '-DCMAKE_CXX_LINKER_LAUNCHER='+launcher,
           '-DCMAKE_EXE_LINKER_FLAGS=--ld-path='+str(a.linker_adapter),
           '-DCMAKE_SHARED_LINKER_FLAGS=--ld-path='+str(a.linker_adapter),
           '-DCMAKE_INSTALL_PREFIX='+str(a.prefix), '-DCMAKE_INSTALL_NAME_DIR='+str(logical_lib),
           '-DLLVM_MODULE_SOURCE='+str(a.llvm_modules), '-DLLVM_INSTALL_PREFIX='+str(staged_prefix),
           '-DLLVM_LIBRARY_DIR='+str(staged_lib)]
    run(cfg+['-UCMAKE_INSTALL_RPATH']); run([a.ninja, '-C', build, '-j', str(a.jobs), 'rpath_check'])
    assert str(staged_lib) in rpaths(build/'rpath_check'), 'fixture did not reproduce stage leak'
    run(cfg+['-DCMAKE_INSTALL_RPATH=@loader_path/../lib;'+str(logical_lib)])
    assert 'main.cpp.o' not in run([a.ninja, '-C', build, '-n', 'rpath_check'])
    run([a.ninja, '-C', build, '-j', str(a.jobs), 'rpath_check', 'rpath_lib'])
    run([a.cmake, '--install', build], extra={'DESTDIR': str(dest)})
    exe = dest / str(a.prefix/'bin/rpath_check').lstrip('/')
    dylib = dest / str(a.prefix/'lib/librpath_lib.dylib').lstrip('/')
    for path in (exe, dylib):
        paths = rpaths(path)
        assert str(staged_lib) not in paths and str(logical_lib) in paths, (path, paths)
    assert '@loader_path/../lib' in rpaths(exe)
    assert str(a.prefix/'lib/librpath_lib.dylib') in run([a.otool, '-D', dylib])
print('PASS: LLVM stage leak reproduced; installed RPATH/LC_ID corrected without object rebuild')
