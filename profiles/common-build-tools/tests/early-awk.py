#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Exercise early native pkgsrc metadata.
"""Query real recipes with the selected awk and a prefix-only search path."""
import argparse
import os
from pathlib import Path
import re
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pkgsrc', type=Path, required=True)
    parser.add_argument('--makeconf', type=Path, required=True)
    parser.add_argument('--host-prefix', type=Path, required=True)
    args = parser.parse_args()
    prefix = args.host_prefix.resolve(strict=True)
    environment = dict(os.environ)
    for name in ('MAKEFLAGS', 'MFLAGS', 'NATIVE_OPSYS_VERSION'):
        environment.pop(name, None)
    environment.update(PATH=f'{prefix}/bin:{prefix}/gnu/bin', LC_ALL='C')
    for package in ('lang/llvm', 'x11/qt6-qtbase'):
        command = [str(prefix / 'bin/bmake'), '-C', str(args.pkgsrc / package),
                   f'MAKECONF={args.makeconf}', f'TOOLS_PLATFORM.awk={prefix}/bin/nawk',
                   'show-var', 'VARNAME=NATIVE_OPSYS_VERSION']
        result = subprocess.run(command, env=environment, capture_output=True,
                                text=True, timeout=120)
        if result.returncode or result.stderr.strip():
            print(f'FAIL: {package}: metadata query returned {result.returncode}', file=sys.stderr)
            print(result.stderr.strip(), file=sys.stderr)
            return 1
        if not re.fullmatch(r'[0-9]{6,}', result.stdout.strip()):
            print(f'FAIL: {package}: missing numeric native OS version', file=sys.stderr)
            return 1
        print(f'PASS: {package}: native OS version {result.stdout.strip()} with selected awk')
    return 0


if __name__ == '__main__':
    sys.exit(main())
