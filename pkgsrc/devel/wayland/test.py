#!/usr/bin/env python3
"""Check that the native Darwin wayland-scanner uses Ports expat, not macOS expat."""
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
import argparse
import os
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--make', required=True,
                        help='host Ports make command that takes PKGPATH and then bmake arguments')
    parser.add_argument('--prefix', help='installed host prefix: also check the wayland-scanner links')
    args = parser.parse_args()
    failures = []
    # A new WRKDIR keeps cached builtin results of an earlier build out of the query.
    with tempfile.TemporaryDirectory() as work:
        lines = subprocess.run([args.make, 'devel/wayland', 'WRKDIR=' + work, '-v', 'OPSYS',
                                '-v', 'USE_BUILTIN.expat'], capture_output=True, text=True,
                               check=True).stdout.splitlines()
    if lines[0] != 'Darwin':
        failures.append('the host Ports make is not a Darwin host build')
    elif lines[1] != 'no':
        failures.append('devel/wayland selects the macOS expat')
    if args.prefix:
        scanner = os.path.join(args.prefix, 'bin/wayland-scanner')
        links = subprocess.run([os.path.join(args.prefix, 'bin/llvm-otool'), '-L', scanner],
                               capture_output=True, text=True, check=True).stdout.split()
        if any(path.startswith('/usr/lib/libexpat') for path in links):
            failures.append('wayland-scanner links /usr/lib/libexpat')
        if not any(path.startswith(os.path.join(args.prefix, 'lib/libexpat')) for path in links):
            failures.append('wayland-scanner does not link the Ports expat')
    if failures:
        print('FAIL: ' + '; '.join(failures))
        return 1
    print('PASS: wayland-scanner uses Ports expat')
    return 0


if __name__ == '__main__':
    sys.exit(main())
