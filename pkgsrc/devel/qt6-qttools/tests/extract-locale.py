#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check that the recipe extract environment writes UTF-8 file names."""
import argparse
import os
import shlex
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
NAME = 'parseqrc/caf\u00e9.js'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--make', type=Path, required=True,
                        help='Ports make wrapper: MAKE PKGPATH -v VARIABLE')
    parser.add_argument('--bsdtar', type=Path, required=True, help='Ports bsdtar')
    args = parser.parse_args()
    result = subprocess.run([str(args.make), 'devel/qt6-qttools', '-v', 'EXTRACT_ENV'],
                            capture_output=True, text=True)
    if result.returncode != 0:
        print('FAIL: cannot evaluate EXTRACT_ENV ' + result.stderr.strip()[:300])
        return 1
    environment = {'PATH': '/usr/bin:/bin', 'LC_ALL': 'C'}
    environment.update(word.split('=', 1) for word in shlex.split(result.stdout.strip()) if '=' in word)
    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        archive = work / 'fixture.tar'
        payload = work / 'payload.js'
        payload.write_text('// fixture\n')
        with tarfile.open(archive, 'w', format=tarfile.PAX_FORMAT) as tar:
            tar.add(payload, arcname=NAME)
        (work / 'out').mkdir()
        extract = subprocess.run([str(args.bsdtar), '-xf', str(archive), '-C', str(work / 'out')],
                                 capture_output=True, text=True, env=environment)
        if extract.returncode != 0 or not (work / 'out' / NAME).is_file():
            print('FAIL: the extract environment cannot write ' + NAME + ': ' + extract.stderr.strip())
            return 1
    print('PASS: the extract environment writes UTF-8 file names')
    return 0


if __name__ == '__main__':
    sys.exit(main())
