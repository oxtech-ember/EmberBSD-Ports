#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check that the real recipe extract command writes UTF-8 member names.

The Ports make environment runs with LC_ALL=C. The common defaults give the
extract step alone a UTF-8 C locale. Without that setting the same command
must fail, so the fixture reproduces the bsdtar conversion error.
"""
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
NAME = 'parseqrc/caf\u00e9.js'
RECIPES = ('audio/flac', 'devel/qt6-qttools')


def extract(make, tree, makeconf, recipe, archive, out, extra=()):
    query = subprocess.run([make, '-C', str(tree / recipe), 'MAKECONF=' + makeconf, *extra,
                            '-v', 'EXTRACT_CMD_DEFAULT'], capture_output=True, text=True)
    if query.returncode != 0 or not query.stdout.strip():
        sys.exit('FAIL: cannot evaluate the extract command of ' + recipe + ': ' + query.stderr.strip()[:300])
    out.mkdir()
    environment = {'PATH': '/usr/bin:/bin', 'LC_ALL': 'C', 'TMPDIR': str(out.parent),
                   'extract_file': str(archive)}
    return subprocess.run(['/bin/sh', '-c', query.stdout.strip()], cwd=out,
                          capture_output=True, text=True, env=environment)


def main():
    if len(sys.argv) != 3:
        sys.exit('Usage: BMAKE=bmake extract-locale.py EXPORTED_PKGSRC MAKECONF')
    make = os.environ.get('BMAKE', 'bmake')
    tree, makeconf = Path(os.path.realpath(sys.argv[1])), os.path.realpath(sys.argv[2])
    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        archive = work / 'fixture.tar'
        payload = work / 'payload.js'
        payload.write_text('// fixture\n')
        with tarfile.open(archive, 'w', format=tarfile.PAX_FORMAT) as tar:
            tar.add(payload, arcname=NAME)
        for index, recipe in enumerate(RECIPES):
            out = work / ('out-%d' % index)
            result = extract(make, tree, makeconf, recipe, archive, out)
            if result.returncode != 0 or not (out / NAME).is_file():
                print('FAIL: ' + recipe + ' cannot extract ' + NAME + ': ' + result.stderr.strip())
                return 1
        old = extract(make, tree, makeconf, RECIPES[0], archive, work / 'out-c', ['EXTRACT_ENV='])
        if old.returncode == 0 or 'converted' not in old.stderr:
            print('FAIL: the C locale fixture does not reproduce the conversion error')
            return 1
    print('PASS: recipe extraction writes UTF-8 member names; the C locale alone fails')
    return 0


if __name__ == '__main__':
    sys.exit(main())
