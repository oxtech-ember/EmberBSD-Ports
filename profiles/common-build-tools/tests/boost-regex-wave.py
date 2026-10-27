#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Build and run real Boost.Regex and Boost.Wave using selected native tools."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
for name in ('prefix', 'staged-prefix', 'sdk', 'work'):
    parser.add_argument('--' + name, type=Path, required=True)
args = parser.parse_args()
assert all(getattr(args, name).is_absolute() for name in ('prefix', 'staged_prefix', 'sdk', 'work'))
args.work.mkdir()
source = Path(__file__).resolve().parent
shutil.copyfile(source / 'boost-regex-wave.cpp', args.work / 'regex-wave.cpp')
shutil.copyfile(source / 'boost-regex-wave.cmake', args.work / 'CMakeLists.txt')
# Present staged libraries and their already-installed matching headers together.
view = args.work / 'view'
view.mkdir()
(view / 'lib').mkdir()
shutil.copytree(args.staged_prefix / 'lib/cmake', view / 'lib/cmake')
for library in (args.staged_prefix / 'lib').iterdir():
    if library.name != 'cmake':
        (view / 'lib' / library.name).symlink_to(library, target_is_directory=library.is_dir())
(view / 'include').symlink_to(args.prefix / 'include', target_is_directory=True)
env = dict(os.environ, PATH=str(args.prefix / 'bin'),
           PKG_CONFIG_PATH=str(args.staged_prefix / 'lib/pkgconfig'),
           DYLD_LIBRARY_PATH=str(args.staged_prefix / 'lib'))
cmake = args.prefix / 'bin/cmake'
subprocess.run([str(cmake), '-S', str(args.work), '-B', str(args.work / 'build'),
                '-G', 'Ninja', '-DCMAKE_MAKE_PROGRAM=' + str(args.prefix / 'bin/ninja'),
                '-DCMAKE_CXX_COMPILER=' + str(args.prefix / 'bin/clang++'),
                '-DCMAKE_LINKER=' + str(args.prefix / 'bin/ld64.lld'),
                '-DCMAKE_AR=' + str(args.prefix / 'bin/llvm-ar'),
                '-DCMAKE_RANLIB=' + str(args.prefix / 'bin/llvm-ranlib'),
                '-DCMAKE_OSX_SYSROOT=' + str(args.sdk),
                '-DCMAKE_FIND_USE_SYSTEM_ENVIRONMENT_PATH=OFF',
                '-DCMAKE_FIND_USE_CMAKE_SYSTEM_PATH=OFF',
                '-DCMAKE_PREFIX_PATH=' + str(view) + ';' + str(args.prefix)],
               env=env, check=True)
subprocess.run([str(cmake), '--build', str(args.work / 'build'), '-j2'], env=env, check=True)
subprocess.run([str(args.work / 'build/boost-regex-wave')], env=env, check=True)
print('PASS: actual Boost.Regex and Boost.Wave without ICU')
