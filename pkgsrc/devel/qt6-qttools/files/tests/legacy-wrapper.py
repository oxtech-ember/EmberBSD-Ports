#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Check real legacy lrelease generation with and without Qt's tool wrapper."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile

if len(sys.argv) != 6:
    raise SystemExit('usage: legacy-wrapper.py CMAKE NINJA CXX QT_PREFIX PATCHED_MACROS')
cmake, ninja, cxx, qt, macros = sys.argv[1:]
if any(not Path(p).is_absolute() for p in sys.argv[1:]):
    raise SystemExit('absolute selected inputs required')
wrapper = os.environ.get('QT_TOOL_TEST_WRAPPER', '')
if not wrapper or not Path(wrapper).is_absolute():
    raise SystemExit('set QT_TOOL_TEST_WRAPPER to the selected native wrapper')
with tempfile.TemporaryDirectory(prefix='qt-legacy-translation-') as tmp:
    root = Path(tmp)
    src = root / 'src'
    src.mkdir()
    (src / 'test.ts').write_text('''<?xml version="1.0"?><TS version="2.1" language="fr"><context><name>Test</name><message><source>Hello</source><translation>Bonjour</translation></message></context></TS>''')
    (src / 'CMakeLists.txt').write_text('''cmake_minimum_required(VERSION 3.29)
project(legacy_translation CXX)
find_package(Qt6 6.12.0 EXACT REQUIRED COMPONENTS Core LinguistTools)
include("${TEST_MACROS}")
qt6_add_translation(qm test.ts)
add_custom_target(translation ALL DEPENDS ${qm})
''')
    for name, selected in (('direct', ''), ('wrapped', wrapper)):
        build = root / name
        subprocess.run([cmake, '-S', str(src), '-B', str(build), '-G', 'Ninja',
                        '-DCMAKE_MAKE_PROGRAM=' + ninja, '-DCMAKE_CXX_COMPILER=' + cxx,
                        '-DCMAKE_PREFIX_PATH=' + qt, '-DTEST_MACROS=' + macros,
                        '-DQT_TOOL_COMMAND_WRAPPER_PATH=' + selected], check=True,
                       stdout=subprocess.DEVNULL)
        subprocess.run([cmake, '--build', str(build)], check=True, stdout=subprocess.DEVNULL)
        if not (build / 'test.qm').is_file() or (build / 'test.qm').stat().st_size == 0:
            raise SystemExit(name + ' did not generate a translation')
print('PASS: legacy lrelease direct and selected wrapper')
