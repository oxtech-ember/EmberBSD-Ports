#!/usr/bin/env python3
"""Check that PLIST matches the wheel that the pinned openTPU source builds."""
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
import argparse
import re
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import zipfile
from pathlib import Path

sys.dont_write_bytecode = True


def expected(source, python, work):
    """Return the pkgsrc PLIST entries for the wheel built from source."""
    dist = work / 'dist'
    subprocess.run([python, '-B', '-c',
                    'import sys; from setuptools import build_meta as b; b.build_wheel(sys.argv[1])',
                    str(dist)], cwd=source, check=True, capture_output=True)
    wheel, = dist.glob('*.whl')
    info = re.compile(r'^[^/]+\.dist-info/')
    entries = []
    for name in zipfile.ZipFile(wheel).namelist():
        if info.match(name):
            entries.append('${PYSITELIB}/${WHEEL_INFODIR}/' + info.sub('', name))
        elif name.endswith('.py'):
            entries += ['${PYSITELIB}/' + name + suffix for suffix in ('', 'c', 'o')]
        else:
            entries.append('${PYSITELIB}/' + name)
    project = tomllib.loads((source / 'pyproject.toml').read_text(encoding='utf-8'))
    entries += ['bin/' + name for name in project['project']['scripts']]
    entries.append('share/doc/${PKGBASE}/SOURCE')
    return sorted(entries)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python', required=True, help='host Python with setuptools')
    parser.add_argument('--distfile', required=True, help='verified openTPU distfile')
    parser.add_argument('--recipe', required=True, help='local-ai/py-opentpu')
    parser.add_argument('--print', action='store_true', help='print the expected PLIST')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as temp:
        work = Path(temp)
        with tarfile.open(args.distfile) as archive:
            archive.extractall(work, filter='data')
        source, = work.glob('openTPU-*')
        want = expected(source, args.python, work)
    if args.print:
        print('@comment $NetBSD$')
        print('\n'.join(want))
        return
    plist = Path(args.recipe) / 'PLIST'
    # The old recipe failed here: it had no PLIST.
    assert plist.is_file(), 'missing ' + str(plist)
    have = [line for line in plist.read_text(encoding='utf-8').splitlines()
            if not line.startswith('@comment')]
    assert have == want, sorted(set(have) ^ set(want))
    print('PASS: PLIST matches the %d files of the openTPU wheel.' % len(want))


if __name__ == '__main__':
    main()
