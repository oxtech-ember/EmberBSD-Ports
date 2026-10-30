#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Check the CMake Fontconfig explicit hint is excluded by Qt's search policy."""
from pathlib import Path
import subprocess
import sys
import tempfile

if len(sys.argv) != 3:
    raise SystemExit('usage: fontconfig-hint.py CMAKE FIND_FONTCONFIG_MODULE')
cmake, module = sys.argv[1:]
with tempfile.TemporaryDirectory(prefix='qt-fontconfig-hint-') as tmp:
    root = Path(tmp)
    external = root / 'external'
    header = external / 'include/fontconfig/fontconfig.h'
    header.parent.mkdir(parents=True)
    header.write_text('#define FC_MAJOR 2\n#define FC_MINOR 1\n#define FC_REVISION 0\n')
    text = Path(module).read_text()
    if text.count('/usr/X11/include') != 1:
        raise SystemExit('selected FindFontconfig no longer has the expected hint')
    modules = root / 'modules'
    modules.mkdir()
    (modules / 'FindFontconfig.cmake').write_text(text.replace('/usr/X11/include', str(external / 'include')))
    library = root / 'libfontconfig.dylib'
    library.touch()
    src = root / 'src'
    src.mkdir()
    (src / 'CMakeLists.txt').write_text('''cmake_minimum_required(VERSION 3.29)
project(check NONE)
set(CMAKE_FIND_USE_CMAKE_SYSTEM_PATH OFF)
set(CMAKE_FIND_USE_CMAKE_ENVIRONMENT_PATH OFF)
set(CMAKE_FIND_USE_SYSTEM_ENVIRONMENT_PATH OFF)
set(Fontconfig_LIBRARY "${TEST_LIBRARY}")
if(IGNORE_HINT)
  set(CMAKE_IGNORE_PATH "${TEST_HINT}")
endif()
find_package(Fontconfig QUIET)
if(IGNORE_HINT AND Fontconfig_INCLUDE_DIR)
  message(FATAL_ERROR "external hint accepted")
elseif(NOT IGNORE_HINT AND NOT Fontconfig_INCLUDE_DIR STREQUAL TEST_HINT)
  message(FATAL_ERROR "control did not use external hint")
endif()
''')
    for setting in ('OFF', 'ON'):
        subprocess.run([cmake, '-S', str(src), '-B', str(root / ('build-' + setting)),
                        '-DCMAKE_MODULE_PATH=' + str(modules), '-DIGNORE_HINT=' + setting,
                        '-DTEST_LIBRARY=' + str(library), '-DTEST_HINT=' + str(external / 'include')],
                       check=True, stdout=subprocess.DEVNULL)
print('PASS: external Fontconfig hint control and exclusion')
