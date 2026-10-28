#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check that configure scripts run with the selected Ports shell (mksh)."""
import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
# These recipes selected bash. Configure runs with the Ports mksh, as pkgsrc does on the host.
PKGPATHS = ('multimedia/libvpx', 'textproc/libplist')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--make', type=Path, required=True,
                        help='Ports bmake wrapper that reads MAKECONF from the environment')
    parser.add_argument('--mk-conf', type=Path, required=True, help='native or cross mk.conf')
    parser.add_argument('--pkgsrc', type=Path, required=True, help='exported pkgsrc tree')
    parser.add_argument('--shell', type=Path, required=True, help='selected Ports mksh')
    args = parser.parse_args()
    environment = dict(os.environ, MAKECONF=str(args.mk_conf))
    for pkgpath in PKGPATHS:
        result = subprocess.run([str(args.make), '-v', 'CONFIG_SHELL'],
                                cwd=args.pkgsrc / pkgpath, env=environment, capture_output=True, text=True)
        values = result.stdout.splitlines()
        if result.returncode != 0 or values != [str(args.shell)]:
            print('FAIL: ' + pkgpath + ' configure shell is not ' + str(args.shell) + ': '
                  + ' | '.join(values) + ' ' + result.stderr.strip()[:300])
            return 1
    print('PASS: ' + ' '.join(PKGPATHS) + ' configure with ' + str(args.shell))
    return 0


if __name__ == '__main__':
    sys.exit(main())
