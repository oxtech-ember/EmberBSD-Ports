#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise real pkg_delete -N and ordinary delete in isolated alternate roots."""
import argparse
from pathlib import Path
import subprocess

p = argparse.ArgumentParser(description=__doc__)
for option in ('pkg-create', 'pkg-add', 'pkg-delete', 'work'):
    p.add_argument('--' + option, type=Path, required=True)
a = p.parse_args()
for item in (a.pkg_create, a.pkg_add, a.pkg_delete, a.work):
    if not item.is_absolute():
        p.error('all paths must be absolute')
a.work.mkdir(parents=True, exist_ok=False)
payload = a.work / 'payload'
(payload / 'share/example/empty').mkdir(parents=True)
(payload / 'share/example/data').write_text('fixture\n')
(a.work / 'plist').write_text('@name ember-keepdir-1.0\nshare/example/data\n@pkgdir share/example/empty\n@dirrm share/example/legacy\n')
(a.work / 'comment').write_text('isolated keepdir test\n')
(a.work / 'description').write_text('isolated package fixture\n')
(a.work / 'build-info').write_text('OPSYS=NetBSD\nMACHINE_ARCH=aarch64\nOS_VERSION=11.0\nPKGTOOLS_VERSION=20260227\n')
archive = a.work / 'fixture.tgz'

def run(*args):
    result = subprocess.run([str(x) for x in args], text=True, capture_output=True, timeout=60)
    if result.returncode:
        raise RuntimeError(f'{args[0]} failed ({result.returncode}): {result.stdout}{result.stderr}')

run(a.pkg_create, '-p', payload, '-I', '/usr/pkg', '-f', a.work / 'plist',
    '-c', a.work / 'comment', '-d', a.work / 'description', '-B', a.work / 'build-info', archive)
for name, flags in (('unregister', ['-N']), ('delete', [])):
    root = a.work / name
    root.mkdir()
    run(a.pkg_add, '-I', '-m', 'NetBSD/aarch64 11.0', '-K', '/usr/pkg/pkgdb',
        '-P', root, '-p', '/usr/pkg', archive)
    prefix = root / 'usr/pkg'
    file = prefix / 'share/example/data'
    empty = prefix / 'share/example/empty'
    legacy = prefix / 'share/example/legacy'
    legacy.mkdir()
    if not file.is_file() or not empty.is_dir():
        raise AssertionError(name + ': fixture was not installed')
    run(a.pkg_delete, '-D', *flags, '-K', '/usr/pkg/pkgdb', '-P', root, 'ember-keepdir-1.0')
    if (root / 'usr/pkg/pkgdb/ember-keepdir-1.0').exists():
        raise AssertionError(name + ': package remains registered')
    if name == 'unregister':
        if file.read_text() != 'fixture\n' or not empty.is_dir() or not legacy.is_dir():
            raise AssertionError('-N must keep both file and empty package directory')
    elif file.exists() or empty.exists() or legacy.exists():
        raise AssertionError('ordinary delete must remove the file and empty package directory')
print('PASS: -N keeps files and package directories; ordinary delete removes both')
