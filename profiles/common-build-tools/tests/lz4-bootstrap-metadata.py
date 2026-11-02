#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Query the real lz4 pkgsrc metadata, without compiling or installing."""
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

CROSS = ['USE_CROSS_COMPILE=yes', 'CROSS_OPSYS=NetBSD', 'CROSS_OS_VERSION=11.0',
    'CROSS_OPSYS_VERSION=110000', 'CROSS_LOWER_OPSYS=netbsd',
    'CROSS_LOWER_OPSYS_VERSUFFIX=netbsd11', 'CROSS_LOWER_VARIANT_VERSION=11',
    'CROSS_LOWER_VENDOR=unknown', 'CROSS_LOWER_OS_VARIANT=netbsd',
    'CROSS_MACHINE_ARCH=aarch64', 'CROSS_OBJECT_FMT=ELF']

class Metadata(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='lz4-bootstrap-metadata-')
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.makeconf = root / 'mk.conf'
        # Recipe-only Darwin control; not a complete Darwin host policy.
        self.makeconf.write_text('_EMBERBSD_DARWIN_BOOTSTRAP_POLICY=1\n')
        self.tree = root / 'pkgsrc'
        self.tree.mkdir()
        for entry in PKGSRC.iterdir():
            if entry.name == 'archivers':
                category = self.tree / 'archivers'
                category.mkdir()
                for child in entry.iterdir():
                    if child.name == 'lz4':
                        shutil.copytree(child, category / 'lz4', symlinks=True)
                    else:
                        (category / child.name).symlink_to(child)
            else:
                (self.tree / entry.name).symlink_to(entry)
        shutil.copyfile(RECIPE, self.tree / 'archivers/lz4/Makefile')

    def query(self, *values):
        return subprocess.run([str(BMAKE), '-C', str(self.tree / 'archivers/lz4'),
            'MAKECONF=' + str(self.makeconf), 'PKG_ADMIN=' + str(PKG_ADMIN),
            'PKGSRC_COMPILER=clang', 'CC_VERSION=clang-23',
            'CLANGBASE=' + str(CLANGBASE), *values,
            '-V', '${TOOL_DEPENDS}', '-V', '${PLIST.cmake}',
            '-V', '${NO_CONFIGURE}', '-V', '${BUILD_TARGET}'],
            text=True, capture_output=True, timeout=60)

    def assert_route(self, flags, cmake):
        result = self.query(*flags)
        self.assertEqual(result.returncode, 0, result.stderr)
        tool_depends, plist, no_configure, targets = result.stdout.splitlines()
        self.assertEqual('../../devel/cmake' in tool_depends, cmake)
        self.assertEqual(plist == 'yes', cmake)
        if not cmake:
            self.assertEqual(no_configure, 'yes')
            self.assertEqual(targets, 'lib-release lz4-release')

    def test_default_uses_cmake(self):
        self.assert_route([], True)

    def test_native_bootstrap_uses_make_without_cmake(self):
        self.makeconf.write_text('_EMBERBSD_DARWIN_BOOTSTRAP_POLICY=1\nEMBERBSD_NATIVE_BOOTSTRAP=yes\n')
        self.assert_route([], False)

    def test_ordinary_cross_keeps_cmake(self):
        self.assert_route(CROSS, True)

    def test_legacy_darwin_bootstrap_keeps_make(self):
        self.assert_route(['EMBERBSD_DARWIN_BOOTSTRAP=yes', 'PKGSRC_COMPILER=clang',
            'CC_VERSION=clang-23', 'EMBERBSD_DARWIN_SEED_AS=/bin/true', 'EMBERBSD_DARWIN_SEED_CC=/bin/true',
            'EMBERBSD_DARWIN_SEED_CXX=/bin/true', 'EMBERBSD_DARWIN_SEED_CPP=/bin/true',
            'EMBERBSD_DARWIN_TOOL.uname=/usr/bin/uname', 'PWD_CMD=/bin/pwd',
            'EMBERBSD_DARWIN_SOURCE_TOOLS=[ awk basename cat chgrp chmod chown cmp cp cut dirname echo egrep env false fgrep find grep head hostname id install ln ls mkdir mv printf pwd rm rmdir sed sh sort tail test touch tr true wc xargs expr sleep date uname digest tar gzcat patch gmake readelf'], False)

    def test_native_bootstrap_refuses_cross(self):
        result = self.query('EMBERBSD_NATIVE_BOOTSTRAP=yes', *CROSS)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('EMBERBSD_NATIVE_BOOTSTRAP cannot be used for cross builds', result.stderr)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('pkgsrc', 'recipe', 'bmake', 'pkg-admin', 'clangbase'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    PKGSRC = args.pkgsrc.resolve(strict=True)
    RECIPE = args.recipe.resolve(strict=True)
    BMAKE = args.bmake.resolve(strict=True)
    PKG_ADMIN = args.pkg_admin.resolve(strict=True)
    CLANGBASE = args.clangbase.resolve(strict=True)
    unittest.main(argv=[__file__])
