#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Exercise the littlefs recipe-to-source archive contract."""
import importlib.util
import hashlib
from pathlib import Path
import tempfile
import unittest

PORTS = Path(__file__).resolve().parents[3]
SOURCE = Path(__file__).with_name('source.py')
SPEC = importlib.util.spec_from_file_location('littlefs_source', SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class LittlefsSourceTests(unittest.TestCase):
    def setUp(self):
        self.owner = MODULE.Owner()
        self.owner.read = lambda path: Path(path).read_bytes()

        def require(condition, message):
            if not condition:
                raise ValueError(message)
        self.owner.require = require

    def test_recipe_maps_release_to_pinned_archive_root(self):
        metadata, patches = self.owner.recipe(PORTS / 'pkgsrc')

        self.assertEqual(metadata['distname'], 'littlefs-2.11.3')
        self.assertEqual(metadata['archive'], 'littlefs-2.11.3.tar.gz')
        self.assertEqual(metadata['archive_root'], 'littlefs-2.11.3')
        self.assertEqual(metadata['size'], 279822)
        self.assertEqual([path.name for path in patches], ['patch-lfs.c', 'patch-lfs_util.h'])
        for path in patches:
            self.assertEqual(metadata['recipe']['patches/' + path.name],
                             hashlib.sha256(path.read_bytes()).hexdigest())

    def test_recipe_rejects_changed_patch_checksum(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'devel/littlefs'
            (root / 'patches').mkdir(parents=True)
            for name in ('Makefile', 'DESCR', 'distinfo'):
                source = PORTS / 'pkgsrc/devel/littlefs' / name
                (root / name).write_bytes(source.read_bytes())
            (root / 'patches').mkdir(exist_ok=True)
            for name in ('patch-lfs.c', 'patch-lfs_util.h'):
                source = PORTS / 'pkgsrc/devel/littlefs/patches' / name
                (root / 'patches' / name).write_bytes(source.read_bytes())
            patch = PORTS / 'pkgsrc/devel/littlefs/patches/patch-lfs_util.h'
            (root / 'patches/patch-lfs_util.h').write_bytes(patch.read_bytes() + b'\n')
            with self.assertRaisesRegex(ValueError, 'patch checksum differs'):
                self.owner.recipe(Path(temporary))

    def test_kernel_patch_uses_netbsd_headers_and_custom_assertion(self):
        patch = (PORTS / 'pkgsrc/devel/littlefs/patches/patch-lfs_util.h').read_text()

        self.assertIn('#if defined(_KERNEL) && defined(__NetBSD__)', patch)
        self.assertIn('#include <sys/systm.h>', patch)
        self.assertIn('!defined(LFS_NO_ASSERT) && !defined(LFS_ASSERT)', patch)

    def test_recipe_rejects_tag_and_archive_version_mismatch(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'devel/littlefs'
            root.mkdir(parents=True)
            for name in ('Makefile', 'DESCR', 'distinfo'):
                source = PORTS / 'pkgsrc/devel/littlefs' / name
                data = source.read_text()
                if name == 'Makefile':
                    data = data.replace('GITHUB_TAG=\trefs/tags/v2.11.3',
                                        'GITHUB_TAG=\trefs/tags/v2.11.2')
                (root / name).write_text(data)
            with self.assertRaisesRegex(ValueError, 'release tag and source version differ'):
                self.owner.recipe(Path(temporary))


if __name__ == '__main__':
    unittest.main()
