#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Exercise the patched library-probe function with real native CMake/compiler."""

import argparse
from pathlib import Path
import re
import shlex
import sys

sys.dont_write_bytecode = True
FILES = Path(__file__).resolve().parents[1] / 'files'
sys.path.insert(0, str(FILES))
import source as owner
arguments = owner.load_sdk(sys.argv[1:])
parser = argparse.ArgumentParser(description=__doc__)
for name in ('host-prefix', 'source', 'work', 'git'):
    parser.add_argument('--' + name, required=True)
options = parser.parse_args(arguments)
from emberbsd_sdk import paths, process
from emberbsd_sdk.host_prefix import load_host_prefix

native = load_host_prefix(options.host_prefix,
    required_roles=('cc', 'cxx', 'ld', 'ar', 'ranlib', 'cmake', 'ninja', 'sh', 'python'))
owner.require(Path(sys.executable).resolve() == Path(native.tool('python')).resolve(),
              'run the native regression with the selected prefix Python')
source = Path(paths.canonical_existing(options.source))
owner.verify_source(source, options.git)
work = Path(paths.build_path(paths.canonical_new(options.work)))
owner.require(not work.exists(), 'native regression work already exists')
paths.real_directory(work.parent)
for path in (native.bundle_root, str(source), str(owner.PORTS)):
    paths.reject_overlap(str(work), path)
work.mkdir()
# Run the actual patched CMake function in isolation. The complete runtime
# configure/build is a separate target check, not simulated by this test.
cmake_source = (source / 'libunwind/cmake/config-ix.cmake').read_text()
function = re.search(r'(?ms)^function\(libunwind_check_library_exists\b.*?^endfunction\(\)', cmake_source)
owner.require(function is not None, 'patched library probe function is absent')
project = work / 'project'
project.mkdir()
(project / 'CMakeLists.txt').write_text('''cmake_minimum_required(VERSION 3.20)
project(UnwindLibraryProbe C)
include(CheckLibraryExists)
set(CMAKE_TRY_COMPILE_TARGET_TYPE STATIC_LIBRARY)
check_library_exists(emberbsd_missing_probe_library emberbsd_probe_symbol "" BEFORE)
if(NOT BEFORE)
  message(FATAL_ERROR "The false-positive static library probe was not reproduced")
endif()
''' + function.group(0) + '''
libunwind_check_library_exists(emberbsd_missing_probe_library emberbsd_probe_symbol "" AFTER)
if(AFTER)
  message(FATAL_ERROR "The patched probe accepted a nonexistent library")
endif()
if(NOT CMAKE_TRY_COMPILE_TARGET_TYPE STREQUAL "STATIC_LIBRARY")
  message(FATAL_ERROR "The library probe changed its caller's compile-only mode")
endif()
libunwind_check_library_exists(c getpid "" NATIVE_LIBC)
if(NOT NATIVE_LIBC)
  message(FATAL_ERROR "The patched probe cannot link the native C library")
endif()
''')
env = process.sanitized_environment()
env.update(PATH=native.path, SHELL=native.tool('sh'), CMAKE_BUILD_PARALLEL_LEVEL='1')
values = dict(CMAKE_C_COMPILER=native.tool('cc'), CMAKE_AR=native.tool('ar'),
    CMAKE_RANLIB=native.tool('ranlib'), CMAKE_LINKER=native.tool('ld'),
    CMAKE_MAKE_PROGRAM=native.tool('ninja'), CMAKE_PROGRAM_PATH=str(Path(native.bundle_root) / 'bin'),
    CMAKE_FIND_USE_SYSTEM_ENVIRONMENT_PATH='OFF', CMAKE_FIND_USE_CMAKE_SYSTEM_PATH='OFF',
    CMAKE_C_FLAGS=shlex.join(native.abi_flags.get('cppflags', []) + native.abi_flags.get('cflags', [])),
    CMAKE_EXE_LINKER_FLAGS=shlex.join(native.abi_flags.get('ldflags', [])))
process.run_logged([native.tool('cmake'), '-S', str(project), '-B', str(work / 'build'), '-G', 'Ninja',
    *['-D' + key + '=' + value for key, value in values.items()]], str(work / 'configure.log'), env=env)
print('PASS: actual CMake library probes reproduce the static false positive, reject the missing library after the patch, retain caller mode and link native libc')
