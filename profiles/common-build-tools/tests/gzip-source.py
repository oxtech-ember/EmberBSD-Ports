#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Check the common gzip source update. Do not execute upstream programs."""
import argparse
import hashlib
import io
import lzma
from pathlib import Path
import re
import shlex
import subprocess
import tarfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
RECIPE = ROOT / 'pkgsrc/archivers/gzip'
XZ_SHA256 = '9aa0cc780dec156b8282844833b342ab7cb08c25d2cd9a1869cdd0df31deff48'
TAR_SHA256 = 'db2d827bc811f348a11da04484bd2c5971ff729a83c5d9f7a3ad6df206b94e92'
ARGS = None


def checked_archive(raw, expected):
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('The pinned source archive differs.')
    return raw


class GzipSourceTests(unittest.TestCase):
    def test_single_current_recipe_and_export_registration(self):
        recipe = (RECIPE / 'Makefile').read_text()
        self.assertRegex(recipe, r'(?m)^DISTNAME=\s*gzip-1\.15$')
        self.assertNotRegex(recipe, r'(?m)^PKGREVISION=')
        replaces = (ROOT / 'pkgsrc/replaces').read_text().splitlines()
        self.assertEqual(replaces.count('archivers/gzip'), 1)
        self.assertNotIn('pkgsrc-gzip-zless-runtime.patch', (ROOT / 'pkgsrc/export.conf').read_text())
        self.assertFalse((ROOT / 'profiles/common-build-tools/patches/pkgsrc-gzip-zless-runtime.patch').exists())

    def test_existing_interfaces_and_bootstrap_archive_are_preserved(self):
        recipe = (RECIPE / 'Makefile').read_text()
        for pattern in (r'EXTRACT_SUFX=\s*\.tar', r'MASTER_SITES=\s*\$\{MASTER_SITE_LOCAL\}',
                        r'GNU_CONFIGURE=\s*yes', r'CONFIGURE_ENV\+=\s*LESS=less',
                        r'MAKE_FLAGS\+=\s*manlinks=so', r'INFO_FILES=\s*yes',
                        r'LICENSE=\s*gnu-gpl-v3', r'CHECK_PERMS=\s*no'):
            self.assertRegex(recipe, pattern)
        for name in ('DESCR', 'PLIST'):
            self.assertEqual((RECIPE / name).read_bytes(),
                (ROOT / 'upstream/pkgsrc/archivers/gzip' / name).read_bytes())
        self.assertFalse((RECIPE / 'patches').exists())

    def test_official_archive_and_distinfo(self):
        packed = checked_archive(ARGS.archive.read_bytes(), XZ_SHA256)
        raw = checked_archive(lzma.decompress(packed), TAR_SHA256)
        self.assertEqual(raw, ARGS.tar.read_bytes())
        info = (RECIPE / 'distinfo').read_text()
        for label, constructor in [('BLAKE2s', hashlib.blake2s), ('SHA512', hashlib.sha512)]:
            self.assertEqual(re.findall(r'^' + label + r' \(gzip-1\.15.tar\) = ([0-9a-f]+)$', info, re.M),
                             [constructor(raw).hexdigest()])
        self.assertEqual(re.findall(r'^Size \(gzip-1\.15.tar\) = (\d+) bytes$', info, re.M), [str(len(raw))])
        self.assertNotIn('patch-', info)
        with self.assertRaises(ValueError):
            checked_archive(packed[:-1] + bytes([packed[-1] ^ 1]), XZ_SHA256)

    def test_upstream_contains_both_retired_patch_repairs(self):
        raw = checked_archive(ARGS.tar.read_bytes(), TAR_SHA256)
        with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
            def source(name):
                return archive.extractfile('gzip-1.15/' + name).read().decode()
            self.assertIn('# include <sys/stat.h>', source('lib/utimens.h'))
            unlzh = source('unlzh.c')
            self.assertIn('memzero (left, (2 * NC - 1) * sizeof *left);', unlzh)
            self.assertIn('memzero (right, (2 * NC - 1) * sizeof *right);', unlzh)
            self.assertIn('memzero (c_table, 4096 * sizeof *c_table);', unlzh)
            self.assertIn('unlinkat (remove_ofname_dfd, fname, 0);', source('gzip.c'))
            self.assertIn('Noteworthy changes in release 1.15 (2026-09-20) [stable]', source('NEWS'))

    def test_complete_export_keeps_the_common_recipe(self):
        if ARGS.pkgsrc is None:
            self.skipTest('Pass --pkgsrc for the full source export check.')
        for path in RECIPE.rglob('*'):
            if path.is_file():
                self.assertEqual(path.read_bytes(), (ARGS.pkgsrc / 'archivers/gzip' / path.relative_to(RECIPE)).read_bytes())
        self.assertFalse((ARGS.pkgsrc / 'archivers/gzip/patches').exists())

    def test_real_native_package_metadata(self):
        if ARGS.bmake is None:
            self.skipTest('Pass --bmake and --makeconf for isolated native metadata.')
        self.assertIsNotNone(ARGS.pkgsrc)
        self.assertIsNotNone(ARGS.makeconf)
        result = subprocess.run([str(ARGS.bmake), '-C', str(ARGS.pkgsrc / 'archivers/gzip'),
            'MAKECONF=' + str(ARGS.makeconf), '-V', '${PKGNAME}', '-V', '${INFO_FILES}',
            '-V', '${CONFIGURE_ENV}', '-V', '${PKG_FAIL_REASON}'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = result.stdout.splitlines()
        self.assertEqual(rows[:2], ['gzip-1.15', 'yes'])
        self.assertIn('LESS=less', shlex.split(rows[2]))
        self.assertEqual(rows[3:], [''])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True, help='Official gzip-1.15.tar.xz')
    parser.add_argument('--tar', type=Path, required=True, help='Uncompressed archive used by pkgsrc')
    parser.add_argument('--pkgsrc', type=Path, help='Complete prepared export')
    parser.add_argument('--bmake', type=Path, help='Explicit selected native bmake')
    parser.add_argument('--makeconf', type=Path, help='Native configuration with private metadata work and pkgdb')
    ARGS, remainder = parser.parse_known_args()
    unittest.main(argv=[__file__, *remainder])
