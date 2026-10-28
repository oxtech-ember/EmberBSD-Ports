#!/usr/bin/env python3
"""Check that native Qt module recipes select CMake tools after compiler selection."""
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
    parser.add_argument('--pkgpath', default='devel/qt6-qttools',
                        help='Qt module recipe that includes x11/qt6-qtbase/Makefile.common')
    args = parser.parse_args()
    result = subprocess.run([args.make, args.pkgpath, '-v', 'PKG_FAIL_REASON'],
                            capture_output=True, text=True)
    if result.returncode != 0:
        print('FAIL: ' + args.pkgpath + ' does not evaluate: ' +
              ' '.join(result.stderr.split())[-200:])
        return 1
    if 'CMake requires' in result.stdout:
        print('FAIL: ' + args.pkgpath + ' validates CMake tools before compiler selection: ' +
              result.stdout.strip())
        return 1
    print('PASS: ' + args.pkgpath + ' selects CMake tools')
    return 0


if __name__ == '__main__':
    sys.exit(main())
