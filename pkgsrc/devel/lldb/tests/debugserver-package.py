#!/usr/bin/env python3
"""Verify the packaged macOS debugserver retains upstream entitlements."""

import argparse
import os
from pathlib import Path
import plistlib
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--archive', required=True)
    parser.add_argument('--bsdtar', required=True)
    parser.add_argument('--entitlements', required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as temporary:
        binary = Path(temporary) / 'debugserver'
        with binary.open('wb') as output:
            subprocess.run([args.bsdtar, '-xOf', args.archive, 'bin/debugserver'],
                           stdout=output, check=True)
        os.chmod(binary, 0o755)
        subprocess.run(['/usr/bin/codesign', '--verify', '--strict', str(binary)],
                       check=True)
        actual = subprocess.run(['/usr/bin/codesign', '-d', '--xml', '--entitlements', '-',
                                 str(binary)], check=True, capture_output=True)
        expected = plistlib.loads(Path(args.entitlements).read_bytes())
        try:
            found = plistlib.loads(actual.stdout)
        except plistlib.InvalidFileException:
            raise SystemExit('packaged debugserver has no readable entitlements')
        if found != expected:
            raise SystemExit('packaged debugserver entitlements differ from upstream')
    print('debugserver package signature and entitlements: PASS')


if __name__ == '__main__':
    main()
