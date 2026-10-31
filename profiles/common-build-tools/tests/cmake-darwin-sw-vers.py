#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check that Darwin CMake reads the host release from /usr/bin/sw_vers.

pkgsrc runs CMake with a search path that has only the tool prefix, so a
bare sw_vers is not found there. The test runs cmake with an empty search
path: cmake_host_system_information must report the release that
/usr/bin/sw_vers prints without an error, and Darwin-Initialize must know
the host version during a configure.
"""
import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
NOISE = ('Could not run', 'command not found')


def run(command, environment):
    return subprocess.run(command, capture_output=True, text=True, env=environment)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cmake', type=Path, required=True, help='absolute Ports cmake executable')
    parser.add_argument('--ninja', type=Path, required=True, help='absolute ninja executable')
    args = parser.parse_args()
    if sys.platform != 'darwin':
        print('SKIP: Darwin only')
        return 0
    release = subprocess.run(['/usr/bin/sw_vers', '-productVersion'], capture_output=True,
                             text=True, check=True).stdout.strip()
    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        (work / 'empty').mkdir()
        environment = {'LC_ALL': 'C', 'PATH': str(work / 'empty'), 'HOME': temporary}
        script = work / 'query.cmake'
        script.write_text('cmake_host_system_information(RESULT r QUERY OS_RELEASE)\n'
                          'message(STATUS "EMBERBSD_RELEASE=${r}")\n')
        result = run([str(args.cmake), '-P', str(script)], environment)
        output = result.stdout + result.stderr
        failures = []
        if result.returncode != 0 or 'EMBERBSD_RELEASE=' + release + '\n' not in result.stdout:
            failures.append('the host query did not report release ' + release)
        failures += ['the host query printed "' + n + '"' for n in NOISE if n in output]
        (work / 'source').mkdir()
        (work / 'source/CMakeLists.txt').write_text(
            'cmake_minimum_required(VERSION 3.20)\nproject(swvers NONE)\n'
            'message(STATUS "EMBERBSD_HOST_OSX=${_CMAKE_HOST_OSX_VERSION}")\n')
        configure = run([str(args.cmake), '-S', str(work / 'source'), '-B', str(work / 'build'),
                         '-G', 'Ninja', '-DCMAKE_MAKE_PROGRAM=' + str(args.ninja)], environment)
        if configure.returncode != 0 or 'EMBERBSD_HOST_OSX=' + release + '\n' not in configure.stdout:
            failures.append('Darwin-Initialize did not read host version ' + release)
        if failures:
            print('FAIL: ' + '; '.join(failures) + '\n' + output + configure.stdout + configure.stderr)
            return 1
    print('PASS: CMake runs /usr/bin/sw_vers without a search path')
    return 0


if __name__ == '__main__':
    sys.exit(main())
