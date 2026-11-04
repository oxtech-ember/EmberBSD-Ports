#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise Qt's real mkspec helper across two in-source configurations."""
import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

PROJECT = '''cmake_minimum_required(VERSION 3.20)
project(mkspecs_fixture NONE)
if(POLICY CMP0177)
  cmake_policy(SET CMP0177 NEW)
endif()
set(INSTALL_MKSPECSDIR share/mkspecs)
set(QT_INSTALL_DIR "${PROJECT_SOURCE_DIR}/build-copy")
function(qt_path_join output first second)
  set(${output} "${first}/${second}" PARENT_SCOPE)
endfunction()
# Keep Qt's configure-time copy separate from the real install destination.
function(qt_copy_or_install kind item destination output)
  install(${kind} "${item}" DESTINATION share/mkspecs ${ARGN})
endfunction()
file(MAKE_DIRECTORY "${PROJECT_SOURCE_DIR}/mkspecs/linux-test")
file(WRITE "${PROJECT_SOURCE_DIR}/mkspecs/linux-test/qmake.conf" "normal")
file(WRITE "${PROJECT_SOURCE_DIR}/mkspecs/qmodule.pri" "final")
include("${PROJECT_SOURCE_DIR}/QtBaseHelpers.cmake")
qt_internal_qtbase_install_mkspecs()
# QtPriHelpers creates the preliminary specs after this macro on first configure.
file(MAKE_DIRECTORY "${PROJECT_SOURCE_DIR}/mkspecs/preliminary")
file(WRITE "${PROJECT_SOURCE_DIR}/mkspecs/preliminary/qmodule.pri" "temporary")
file(WRITE "${PROJECT_SOURCE_DIR}/mkspecs/preliminary/qconfig.pri" "temporary")
'''


def exercise(cmake, helper, copy_enabled, expect_leak):
    with tempfile.TemporaryDirectory(prefix='qt-mkspecs-') as temporary:
        root = Path(temporary)
        source = root / 'source'
        source.mkdir()
        (source / 'CMakeLists.txt').write_text(PROJECT)
        shutil.copyfile(helper, source / 'QtBaseHelpers.cmake')
        for stage in (1, 2):
            destination = root / ('install' + str(stage))
            subprocess.run([cmake, '-S', str(source), '-B', str(source),
                            '-DCMAKE_INSTALL_PREFIX=' + str(destination),
                            '-DQT_WILL_INSTALL=' + ('TRUE' if copy_enabled else 'FALSE')],
                           check=True, stdout=subprocess.DEVNULL)
            subprocess.run([cmake, '--install', str(source)], check=True, stdout=subprocess.DEVNULL)
            installed = destination / 'share/mkspecs'
            assert (installed / 'linux-test/qmake.conf').read_text() == 'normal'
            assert (installed / 'qmodule.pri').read_text() == 'final'
            assert (source / 'mkspecs/preliminary/qmodule.pri').is_file()
            leak = (installed / 'preliminary/qmodule.pri').exists()
            leak |= (installed / 'preliminary/qconfig.pri').exists()
            assert leak == (stage == 2 and expect_leak), (stage, copy_enabled, leak)
            if copy_enabled:
                copied = source / 'build-copy/share/mkspecs'
                assert (copied / 'linux-test/qmake.conf').read_text() == 'normal'
                assert (copied / 'qmodule.pri').read_text() == 'final'
                assert (copied / 'preliminary/qmodule.pri').exists() == (stage == 2 and expect_leak)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('cmake', help='selected CMake executable')
    parser.add_argument('qtbase_source', type=Path, help='unpatched QtBase source directory')
    parser.add_argument('patch', type=Path, help='pkgsrc patch to test')
    args = parser.parse_args()
    original = args.qtbase_source / 'cmake/QtBaseHelpers.cmake'
    with tempfile.TemporaryDirectory(prefix='qt-mkspecs-patch-') as temporary:
        root = Path(temporary)
        (root / 'cmake').mkdir()
        shutil.copyfile(original, root / 'cmake/QtBaseHelpers.cmake')
        subprocess.run(['patch', '-s', '-p0', '-i', str(args.patch.resolve())], cwd=root, check=True)
        for copy_enabled in (False, True):
            exercise(args.cmake, original, copy_enabled, True)
            exercise(args.cmake, root / 'cmake/QtBaseHelpers.cmake', copy_enabled, False)
    print('PASS: original leaks on reconfigure; patched install and copy retain only final specs')


if __name__ == '__main__':
    main()
