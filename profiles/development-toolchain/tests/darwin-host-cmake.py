#!/usr/bin/env python3
"""Check that Darwin host recipes that request the cmake tool use the installed Ports CMake."""
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
import argparse
import subprocess
import sys

sys.dont_write_bytecode = True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--make', required=True,
                        help='host Ports make command that takes PKGPATH and then bmake arguments')
    parser.add_argument('--pkgpath', default='x11/qt6-qtbase',
                        help='recipe that requests USE_TOOLS cmake without devel/cmake/build.mk')
    args = parser.parse_args()
    result = subprocess.run([args.make, args.pkgpath, '-v', 'LOCALBASE', '-v', 'TOOLS_PLATFORM.cmake',
                             '-v', 'PKG_FAIL_REASON'], capture_output=True, text=True)
    lines = result.stdout.splitlines()
    if result.returncode != 0 or len(lines) < 3:
        print('FAIL: ' + args.pkgpath + ' has no host CMake provider: ' +
              ' '.join(result.stderr.split())[-200:])
        return 1
    localbase, cmake, reasons = lines[0], lines[1], lines[2]
    if cmake != localbase + '/bin/cmake' or 'EMBERBSD_BUILD_CMAKE' in reasons:
        print('FAIL: ' + args.pkgpath + ' selects CMake ' + repr(cmake) + ' ' + reasons)
        return 1
    print('PASS: ' + args.pkgpath + ' uses ' + cmake)
    return 0


if __name__ == '__main__':
    sys.exit(main())
