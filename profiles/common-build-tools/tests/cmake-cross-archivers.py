#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check pkgsrc cross CMake arguments with real static-library probes."""
import argparse
import os
from pathlib import Path
import shlex
import subprocess

p = argparse.ArgumentParser(description=__doc__)
for name in ('bmake', 'package', 'makeconf', 'sdk', 'host-prefix', 'cxx', 'target-bin', 'work'):
    p.add_argument('--' + name, required=True)
a = p.parse_args()

def query(variable):
    return subprocess.check_output([a.bmake, '-C', a.package, 'MAKECONF=' + a.makeconf,
                                    'EMBER_LLVM_CXX_STAGE=', '-v', variable], text=True).strip()

arguments = shlex.split(query('CMAKE_CONFIGURE_ARGS'))
ar, ranlib = query('AR'), query('RANLIB')
for variable, value in [('CMAKE_AR', ar), ('CMAKE_RANLIB', ranlib)]:
    assert any(arg == '-D' + variable + ':FILEPATH=' + value for arg in arguments), (variable, arguments)
    assert os.path.isabs(value) and os.access(value, os.X_OK), value
for tool in ('llvm-ar', 'llvm-ranlib'):
    assert (Path(a.target_bin) / tool).exists(), tool
root = Path(a.work)
root.mkdir()
source = root / 'source'
source.mkdir()
(source / 'CMakeLists.txt').write_text('''cmake_minimum_required(VERSION 3.20)\nproject(archiver CXX)\ninclude(CheckCXXCompilerFlag)\ncheck_cxx_compiler_flag(-funwind-tables SUPPORTS_UNWIND_TABLES)\nif(NOT SUPPORTS_UNWIND_TABLES)\n  message(FATAL_ERROR "Unwind table check failed")\nendif()\n''')
runner = Path(a.sdk) / 'scripts/run-native-check.py'
python = Path(a.host_prefix) / 'bin/python3.15'
base = [str(python), str(runner), '--host-prefix', a.host_prefix, '--tool', 'cmake',
        '--required-role', 'ninja', '--cwd', str(source)]
cmake = ['-G', 'Ninja', '-S', str(source), '-DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY',
         '-DCMAKE_CXX_COMPILER=' + a.cxx, '-DCMAKE_PROGRAM_PATH=' + a.target_bin]
for name, args, success in [('selected', arguments, True),
                            ('target-only', [x for x in arguments if not x.startswith(('-DCMAKE_AR:', '-DCMAKE_RANLIB:'))] +
                             ['-DCMAKE_AR=' + str(Path(a.target_bin) / 'llvm-ar'),
                              '-DCMAKE_RANLIB=' + str(Path(a.target_bin) / 'llvm-ranlib')], False)]:
    cmd = base + ['--log', str(root / (name + '.log')), '--bindings', str(root / (name + '-bindings')),
                  '--', *cmake, '-B', str(root / (name + '-build')), *args]
    result = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if (result.returncode == 0) != success:
        raise SystemExit(name + ': unexpected result; inspect ' + str(root / (name + '.log')) + '\n' + result.stderr)
    if success:
        cache = (root / (name + '-build/CMakeCache.txt')).read_text()
        assert 'CMAKE_AR:FILEPATH=' + ar in cache and 'CMAKE_RANLIB:FILEPATH=' + ranlib in cache
        log = (root / (name + '-build/CMakeFiles/CMakeConfigureLog.yaml')).read_text()
        assert ar in log and ranlib in log, 'selected archive commands were not executed'
    else:
        log = (root / (name + '-build/CMakeFiles/CMakeConfigureLog.yaml')).read_text()
        assert 'llvm-ar' in log and ('exec format error' in log.lower() or 'not executable' in log.lower()), \
            'negative control failed for a different reason'
print('PASS: actual pkgsrc cross arguments select runnable ar/ranlib and reject target-only archivers')
