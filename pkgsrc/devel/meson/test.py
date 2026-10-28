#!/usr/bin/env python3
"""Check that Darwin Meson consumers get otool and install_name_tool."""
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
import argparse
import os
import subprocess
import sys

sys.dont_write_bytecode = True
NAMES = ('install_name_tool', 'otool')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--make', required=True,
                        help='host Ports make command that takes PKGPATH and then bmake arguments')
    parser.add_argument('--pkgpath', default='devel/wayland', help='Meson consumer recipe')
    args = parser.parse_args()
    query = [args.make, args.pkgpath, '-v', 'TOOLS_CREATE']
    for name in NAMES:
        query += ['-v', 'TOOLS_PATH.' + name]
    lines = subprocess.run(query, capture_output=True, text=True, check=True).stdout.splitlines()
    created, paths = lines[0].split(), dict(zip(NAMES, lines[1:]))
    # Meson install runs both commands by name for Mach-O rpaths.
    missing = [n for n in NAMES if n not in created or not os.access(paths[n], os.X_OK)]
    if missing:
        print('FAIL: Meson install on Darwin lacks ' + ' '.join(missing))
        return 1
    subprocess.run([paths['otool'], '-l', paths['otool']], capture_output=True, check=True)
    print('PASS: ' + ' '.join(n + '=' + paths[n] for n in NAMES))
    return 0


if __name__ == '__main__':
    sys.exit(main())
