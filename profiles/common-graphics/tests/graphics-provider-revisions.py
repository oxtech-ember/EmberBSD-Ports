#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Query real common graphics provider revision contracts.
import argparse
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('pkgsrc', 'bmake', 'makeconf', 'awk'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    for package, identity, previous in [('devel/libffi', 'libffi 3.8.0nb2', '1'),
                                         ('x11/libdrm', 'libdrm 2.4.134nb8', '7')]:
        base = [str(args.bmake), '-C', str(args.pkgsrc / package),
                'MAKECONF=' + str(args.makeconf), 'TOOLS_PLATFORM.awk=' + str(args.awk),
                'show-vars', 'VARNAMES=PKG_FAIL_REASON']
        result = subprocess.run(base, capture_output=True, text=True, check=True, timeout=45)
        assert not result.stdout.strip(), (package, result.stdout)
        result = subprocess.run(base + ['PKGREVISION=' + previous], capture_output=True, text=True, check=True, timeout=45)
        assert identity in result.stdout, (package, result.stdout)
        print('PASS:', identity, 'current provider accepted, previous revision refused')



if __name__ == '__main__':
    main()
