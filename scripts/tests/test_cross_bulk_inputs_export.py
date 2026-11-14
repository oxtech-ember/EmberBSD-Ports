#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check the build-input digest on real recipes of a prepared pkgsrc export.

Set CROSS_BULK_TEST_PKGSRC to a scratch export from scripts/prepare-pkgsrc.py
and CROSS_BULK_TEST_MAKECONF to a matching mk.conf; CROSS_BULK_TEST_BMAKE
names bmake (default: bmake in PATH). The test edits recipe files of that
export and restores them; do not point it at an export that a build uses.
Without these variables the test prints SKIP.
"""
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def names():
    text = (ROOT / 'scripts/cross-bulk.sh').read_text()
    return re.search(r"^build_input_names='(.*)'$", text, re.M).group(1)


def digest(pkgsrc, bmake, env, path):
    directory = str(pkgsrc / path)
    selected = names()
    values = subprocess.run([bmake, '-C', directory, 'show-vars', 'VARNAMES=' + selected],
                            stdin=subprocess.DEVNULL, capture_output=True, text=True, env=env,
                            check=True).stdout
    wrkdir = subprocess.run([bmake, '-C', directory, 'show-var', 'VARNAME=WRKDIR'],
                            stdin=subprocess.DEVNULL, capture_output=True, text=True, env=env,
                            check=True).stdout.strip()
    result = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/cross-bulk-inputs.py'),
                             '--pkgsrc', str(pkgsrc), '--wrkdir', wrkdir, '--names', selected],
                            input=values, capture_output=True, text=True, env=env)
    assert result.returncode == 0 and result.stdout.strip(), (path, result.stderr[-500:])
    return result.stdout.strip()


class Edit:
    """Replace the first match of a pattern in a file until the block ends."""

    def __init__(self, path, pattern, replacement):
        self.path, self.pattern, self.replacement = path, pattern, replacement

    def __enter__(self):
        self.original = self.path.read_bytes()
        text = self.original.decode()
        changed, count = re.subn(self.pattern, self.replacement, text, count=1, flags=re.M)
        assert count == 1, (self.path, self.pattern)
        self.path.write_text(changed)

    def __exit__(self, *exc):
        self.path.write_bytes(self.original)


def bump(match):
    return match.group(1) + str(int(match.group(2)) + 1)


# Recipe, file, revision assignment, and whether a bump keeps the digest.
CASES = (
    ('lang/python315', 'Makefile', r'^(PKGREVISION=\s*)([0-9]+)', True),
    ('graphics/MesaLib', 'mesa-source.mk', r'^(MESA_PORT_REVISION=\s*)([0-9]+)', True),
    ('x11/qt6-qtbase', 'Makefile', r'^(PKGREVISION=\s*)([0-9]+)', True),
    ('x11/qt6-qtbase', 'package-revisions.mk', r'^(QTBASE_RUNTIME_REVISION=\s*)([0-9]+)', True),
)


def main():
    if not os.environ.get('CROSS_BULK_TEST_PKGSRC') or not os.environ.get('CROSS_BULK_TEST_MAKECONF'):
        print('SKIP: set CROSS_BULK_TEST_PKGSRC and CROSS_BULK_TEST_MAKECONF to check real recipes')
        return
    pkgsrc = Path(os.environ['CROSS_BULK_TEST_PKGSRC'])
    bmake = os.environ.get('CROSS_BULK_TEST_BMAKE', 'bmake')
    env = dict(os.environ, MAKECONF=os.environ['CROSS_BULK_TEST_MAKECONF'])
    for path, name, pattern, same in CASES:
        base = digest(pkgsrc, bmake, env, path)
        assert digest(pkgsrc, bmake, env, path) == base, path
        with Edit(pkgsrc / path / name, pattern, bump):
            assert (digest(pkgsrc, bmake, env, path) == base) == same, (path, name)
        # A comment on the revision line names a rebuild reason.
        with Edit(pkgsrc / path / name, pattern + r'$', r'\g<0> # rebuild reason'):
            assert digest(pkgsrc, bmake, env, path) != base, (path, name, 'comment')
        patches = sorted((pkgsrc / path / 'patches').glob('patch-*'))
        if patches:
            with Edit(patches[0], r'\Z', '\n'):
                assert digest(pkgsrc, bmake, env, path) != base, (path, patches[0].name)
        assert digest(pkgsrc, bmake, env, path) == base, (path, 'restored')
    # lmdb substitutes PKGVERSION (SUBST_VARS.pc) into lmdb.pc before the build:
    # its revision reaches the package files.
    lmdb = pkgsrc / 'databases/lmdb/Makefile'
    if re.search(r'^SUBST_VARS[^=]*=.*\bPKGVERSION\b', lmdb.read_text(), re.M):
        with Edit(lmdb, r'^(PKGNAME=.*\n|DISTNAME=.*\n)', '\\g<0>PKGREVISION=\t1\n'):
            first = digest(pkgsrc, bmake, env, 'databases/lmdb')
            with Edit(lmdb, r'^(PKGREVISION=\s*)([0-9]+)', bump):
                assert digest(pkgsrc, bmake, env, 'databases/lmdb') != first, 'lmdb'
    print('PASS: real recipes keep the digest for revision-only changes; comments, patches '
          'and substituted revisions change it')


if __name__ == '__main__':
    main()
