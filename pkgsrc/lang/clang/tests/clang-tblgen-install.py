#!/usr/bin/env python3
"""Check that lang/clang installs clang-tblgen with the selected LLVM CMake rules."""
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
import argparse
import os
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
# The same add_tablegen() call as clang/utils/TableGen, without the sources.
PROBE = '''cmake_minimum_required(VERSION 3.20)
project(probe C CXX)
find_package(LLVM REQUIRED CONFIG)
list(APPEND CMAKE_MODULE_PATH ${LLVM_CMAKE_DIR})
include(AddLLVM)
include(TableGen)
file(WRITE ${CMAKE_BINARY_DIR}/probe.cpp "int main() { return 0; }\\n")
set(LLVM_LINK_COMPONENTS Support)
add_tablegen(clang-tblgen CLANG DESTINATION bin EXPORT Clang ${CMAKE_BINARY_DIR}/probe.cpp)
'''
OPTIONS = ('LLVM_BUILD_UTILS', 'LLVM_INSTALL_TOOLCHAIN_ONLY')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--make', required=True,
                        help='host Ports make command that takes PKGPATH and then bmake arguments')
    parser.add_argument('--prefix', required=True,
                        help='native prefix with LLVM CMake files, cmake, ninja and clang')
    args = parser.parse_args()
    lines = subprocess.run([args.make, 'lang/clang', '-v', 'PKGDIR', '-v', 'CMAKE_CONFIGURE_ARGS'],
                           capture_output=True, text=True, check=True).stdout.splitlines()
    pkgdir, recipe = lines[0], lines[1].split()
    selected = [a for a in recipe if a.split('=', 1)[0].split(':', 1)[0] in ['-D' + o for o in OPTIONS]]
    tool = lambda name: os.path.join(args.prefix, 'bin', name)
    with tempfile.TemporaryDirectory() as work:
        with open(os.path.join(work, 'CMakeLists.txt'), 'w') as source:
            source.write(PROBE)
        env = dict(PATH=os.path.join(args.prefix, 'bin') + ':/usr/bin:/bin', HOME=work)
        subprocess.run([tool('cmake'), '-S', work, '-B', work + '/build', '-G', 'Ninja',
                        '-DCMAKE_MAKE_PROGRAM=' + tool('ninja'), '-DCMAKE_C_COMPILER=' + tool('clang'),
                        '-DCMAKE_CXX_COMPILER=' + tool('clang++'),
                        '-DCMAKE_INSTALL_NAME_TOOL=' + tool('llvm-install-name-tool'),
                        '-DLLVM_DIR=' + os.path.join(args.prefix, 'lib/cmake/llvm'), *selected],
                       env=env, capture_output=True, check=True)
        with open(work + '/build/cmake_install.cmake') as rules:
            installed = 'clang-tblgen' in rules.read()
    with open(os.path.join(pkgdir, 'PLIST')) as plist:
        listed = 'bin/clang-tblgen' in plist.read().split()
    if not installed or not listed:
        print('FAIL: lang/clang does not install bin/clang-tblgen (options: %s; PLIST: %s)'
              % (' '.join(selected), listed))
        return 1
    print('PASS: lang/clang installs bin/clang-tblgen with ' + ' '.join(selected))
    return 0


if __name__ == '__main__':
    sys.exit(main())
