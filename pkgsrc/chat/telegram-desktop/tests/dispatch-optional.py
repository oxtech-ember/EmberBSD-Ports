#!/usr/bin/env python3
"""Configure the real patched dispatch module with and without a package."""
import argparse
from pathlib import Path
import subprocess
import tempfile

ap = argparse.ArgumentParser()
ap.add_argument('--source', type=Path, required=True, help='Telegram source root')
ap.add_argument('--patch', type=Path, required=True, help='patch executable')
ap.add_argument('--cmake', type=Path, required=True, help='CMake executable')
ap.add_argument('--recipe', type=Path, required=True, help='Telegram Ports recipe')
a = ap.parse_args()
with tempfile.TemporaryDirectory(prefix='telegram-dispatch-test-') as temp:
    root = Path(temp)
    module = root / 'cmake/external/dispatch/CMakeLists.txt'
    module.parent.mkdir(parents=True)
    module.write_bytes((a.source / 'cmake/external/dispatch/CMakeLists.txt').read_bytes())
    subprocess.run([str(a.patch), '-p0', '-i', str(a.recipe / 'patches/patch-cmake_external_dispatch_CMakeLists.txt')], cwd=root, check=True, capture_output=True)
    (root / 'CMakeLists.txt').write_text('''cmake_minimum_required(VERSION 3.16)
project(dispatch_regression NONE)
set(DESKTOP_APP_USE_PACKAGED ON)
set(third_party_loc "${CMAKE_CURRENT_SOURCE_DIR}/bundled")
function(find_library name)
  if(PRESENT)
    set(${name} "/tmp/libdispatch.so" PARENT_SCOPE)
  else()
    set(${name} "${name}-NOTFOUND" PARENT_SCOPE)
  endif()
endfunction()
function(find_path name)
  if(PRESENT)
    set(${name} "/tmp/include" PARENT_SCOPE)
  else()
    set(${name} "${name}-NOTFOUND" PARENT_SCOPE)
  endif()
endfunction()
function(execute_process)
  message(FATAL_ERROR "bundled dispatch build was invoked")
endfunction()
add_subdirectory(cmake/external/dispatch)
if(PRESENT AND NOT TARGET desktop-app::external_dispatch)
  message(FATAL_ERROR "system dispatch target missing")
endif()
if(NOT PRESENT AND TARGET desktop-app::external_dispatch)
  message(FATAL_ERROR "absent optional dispatch created a target")
endif()
''')
    (root / 'bundled/dispatch').mkdir(parents=True)
    for flag in ('OFF', 'ON'):
        subprocess.run([str(a.cmake), '-S', str(root), '-B', str(root / ('build-' + flag)), '-DPRESENT=' + flag], check=True, capture_output=True)
    print('PASS: optional missing and present system dispatch; bundled build not executed')
