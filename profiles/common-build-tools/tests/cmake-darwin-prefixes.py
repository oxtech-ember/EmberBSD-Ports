#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check that Darwin CMake does not search Homebrew, Fink or MacPorts."""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
FOREIGN = ('/opt/homebrew', '/sw', '/opt/local')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cmake', type=Path, required=True, help='absolute Ports cmake executable')
    parser.add_argument('--platform-file', type=Path,
                        help='check this Modules/Platform/Darwin.cmake in a copy of the CMake tree')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        cmake = args.cmake
        if args.platform_file:
            # CMake loads its platform modules from <prefix>/share/cmake-<version> next to the executable.
            prefix = args.cmake.resolve().parent.parent
            roots = sorted((prefix / 'share').glob('cmake-*'))
            if len(roots) != 1:
                print('FAIL: expected one CMake root in ' + str(prefix / 'share'))
                return 1
            (work / 'cmake/bin').mkdir(parents=True)
            cmake = work / 'cmake/bin/cmake'
            shutil.copy2(args.cmake.resolve(), cmake)
            shutil.copytree(roots[0], work / 'cmake/share' / roots[0].name, symlinks=True)
            shutil.copy2(args.platform_file, work / 'cmake/share' / roots[0].name / 'Modules/Platform/Darwin.cmake')
        brew_prefix = work / 'brew prefix'
        brew_prefix.mkdir()
        marker = work / 'brew-ran'
        (work / 'bin').mkdir()
        brew = work / 'bin/brew'
        brew.write_text('#!/bin/sh\n: > "' + str(marker) + '"\nprintf "%s\\n" "' + str(brew_prefix) + '"\n')
        brew.chmod(0o755)
        (work / 'source').mkdir()
        (work / 'source/CMakeLists.txt').write_text(
            'cmake_minimum_required(VERSION 3.20)\nproject(prefixes NONE)\n'
            'message(STATUS "EMBERBSD_PREFIXES=${CMAKE_SYSTEM_PREFIX_PATH}")\n')
        environment = dict(os.environ, LC_ALL='C', PATH=str(work / 'bin') + ':' + str(args.cmake.resolve().parent))
        generator = ['-G', 'Ninja', '-DCMAKE_MAKE_PROGRAM=' + str(args.cmake.resolve().parent / 'ninja')]
        result = subprocess.run([str(cmake), '-S', str(work / 'source'), '-B', str(work / 'build')] + generator,
                                capture_output=True, text=True, env=environment)
        lines = [line for line in result.stdout.splitlines() if 'EMBERBSD_PREFIXES=' in line]
        if result.returncode != 0 or len(lines) != 1:
            print('FAIL: cmake did not configure\n' + result.stdout + result.stderr)
            return 1
        prefixes = lines[0].split('EMBERBSD_PREFIXES=', 1)[1].split(';')
        found = [prefix for prefix in prefixes if prefix in FOREIGN or prefix == str(brew_prefix)]
        if marker.exists() or found:
            print('FAIL: Darwin CMake ran brew or searches ' + ' '.join(found))
            return 1
        decoy = work / 'root/usr/local/lib/cmake/EmberDecoy'
        decoy.mkdir(parents=True)
        (decoy / 'EmberDecoyConfig.cmake').write_text('set(EmberDecoy_FOUND TRUE)\n')
        (work / 'source/CMakeLists.txt').write_text(
            'cmake_minimum_required(VERSION 3.20)\nproject(prefixes NONE)\n'
            'find_package(EmberDecoy CONFIG QUIET)\n'
            'message(STATUS "DECOY=${EmberDecoy_FOUND}")\n')
        common = [str(cmake), '-S', str(work / 'source'),
                  '-DEMBERBSD_CMAKE_NATIVE_TOOLS=ON',
                  '-DCMAKE_FIND_ROOT_PATH=' + str(work / 'root')] + generator
        for explicit, expected in ((False, '0'), (True, '1')):
            command = common + ['-B', str(work / ('explicit' if explicit else 'native'))]
            if explicit:
                command.append('-DCMAKE_PREFIX_PATH=/usr/local')
            result = subprocess.run(command, capture_output=True, text=True, env=environment)
            if result.returncode or ('DECOY=' + expected) not in result.stdout:
                print('FAIL: native or explicit prefix routing\n' + result.stdout + result.stderr)
                return 1
        if args.platform_file:
            # Model a CMake installation deliberately rooted at /usr/local.
            unix_paths = work / 'cmake/share' / roots[0].name / 'Modules/Platform/UnixPaths.cmake'
            original = unix_paths.read_text()
            marker_line = 'unset(_cmake_running_in_build_tree)'
            if marker_line not in original:
                print('FAIL: cannot model selected CMake installation prefix')
                return 1
            unix_paths.write_text(original.replace(marker_line, marker_line +
                                                  '\nset(_CMAKE_INSTALL_DIR "/usr/local")', 1))
            result = subprocess.run(common + ['-B', str(work / 'selected')],
                                    capture_output=True, text=True, env=environment)
            if result.returncode or 'DECOY=1' not in result.stdout:
                print('FAIL: selected /usr/local CMake prefix\n' + result.stdout + result.stderr)
                return 1
    print('PASS: Darwin CMake excludes ambient foreign prefixes and honors explicit paths')
    return 0


if __name__ == '__main__':
    sys.exit(main())
