#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Check the native KConfig compiler's direct and wrapped CMake rules."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile

if len(sys.argv) != 7:
    raise SystemExit('usage: compiler-wrapper.py CMAKE NINJA CXX QT_PREFIX PATCHED_MACROS TOOL_TARGETS')
cmake, ninja, cxx, qt, macros, targets = sys.argv[1:]
if any(not Path(p).is_absolute() for p in sys.argv[1:]):
    raise SystemExit('absolute selected inputs required')
wrapper = os.environ.get('QT_TOOL_TEST_WRAPPER', '')
if not wrapper or not Path(wrapper).is_absolute():
    raise SystemExit('set QT_TOOL_TEST_WRAPPER to the selected native wrapper')
with tempfile.TemporaryDirectory(prefix='kconfig-compiler-rule-') as tmp:
    root = Path(tmp)
    src = root / 'src'
    src.mkdir()
    (src / 'example.kcfg').write_text('''<?xml version="1.0"?><kcfg xmlns="http://www.kde.org/standards/kcfg/1.0"><kcfgfile name="example"/><group name="General"><entry name="Count" type="Int"><default>3</default></entry></group></kcfg>''')
    (src / 'example.kcfgc').write_text('File=example.kcfg\nClassName=ExampleSettings\n')
    (src / 'CMakeLists.txt').write_text('''cmake_minimum_required(VERSION 3.29)
project(kconfig_rule CXX)
find_package(Qt6 6.12.0 EXACT REQUIRED COMPONENTS Core)
include("${TEST_TARGETS}")
include("${TEST_MACROS}")
kconfig_add_kcfg_files(generated example.kcfgc)
add_custom_target(generate ALL DEPENDS ${generated})
''')
    for name, selected in (('direct', ''), ('wrapped', wrapper)):
        build = root / name
        subprocess.run([cmake, '-S', str(src), '-B', str(build), '-G', 'Ninja',
                        '-DCMAKE_MAKE_PROGRAM=' + ninja, '-DCMAKE_CXX_COMPILER=' + cxx,
                        '-DCMAKE_PREFIX_PATH=' + qt, '-DTEST_MACROS=' + macros,
                        '-DTEST_TARGETS=' + targets, '-DQT_TOOL_COMMAND_WRAPPER_PATH=' + selected],
                       check=True, stdout=subprocess.DEVNULL)
        subprocess.run([cmake, '--build', str(build)], check=True, stdout=subprocess.DEVNULL)
        if not all((build / ('example.' + suffix)).is_file() for suffix in ('cpp', 'h')):
            raise SystemExit(name + ' did not generate KConfig files')
print('PASS: KConfig compiler direct and selected wrapper')
