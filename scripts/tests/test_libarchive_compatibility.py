# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Verify legacy libarchive payload reuse against the current export."""
import importlib.util
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(os.environ['EMBERBSD_SDK_SOURCE']) / 'src'))
from emberbsd_sdk import sourceprep
from emberbsd_sdk.errors import SDKError

spec = importlib.util.spec_from_file_location('libarchive_source', ROOT / 'scripts/libarchive-source.py')
owner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(owner)


class CompatibilityTest(unittest.TestCase):
    def test_scoped_recipe_and_origin(self):
        with tempfile.TemporaryDirectory(dir=os.environ['EMBERBSD_TEST_WORK']) as tmp:
            root = Path(tmp)
            export = root / 'export'
            recipe = export / owner.PACKAGE
            (recipe / 'files').mkdir(parents=True)
            (recipe / 'Makefile').write_text('recipe\n')
            (recipe / 'files/source.c').write_text('payload\n')
            selector = owner.module(ROOT / 'scripts/pkgsrc-source-identity.py', 'test_scoped_identity')
            source = root / 'prepared'
            shutil.copytree(recipe / 'files', source)
            scoped = {'effective': selector.effective_package_identity(export, owner.PACKAGE, '1' * 40),
                      'owner_sha256': '3' * 64}
            record = sourceprep.write_prepared_tree_receipt(source, package=owner.PACKAGE, identity=scoped)
            current = {'upstream': '2' * 40, 'owner_sha256': '3' * 64}
            def do_export(command, **kwargs):
                shutil.copytree(export, Path(command[3]))
            with patch.object(owner, 'selected_identity', return_value=current), \
                    patch.object(owner.subprocess, 'run', side_effect=do_export):
                self.assertEqual(record, owner.verify(source, '/sdk', '/git', '/patch'))
                current['owner_sha256'] = '5' * 64
                self.assertEqual(record, owner.verify(source, '/sdk', '/git', '/patch'))
                (recipe / 'Makefile').write_text('recipe\nCOMMENT=changed\n')
                self.assertEqual(record, owner.verify(source, '/sdk', '/git', '/patch'))
                (recipe / 'files/source.c').write_text('changed payload\n')
                with self.assertRaisesRegex(ValueError, 'differs from current effective source'):
                    owner.verify(source, '/sdk', '/git', '/patch')

    def test_legacy_comparison_and_payload_integrity(self):
        with tempfile.TemporaryDirectory(dir=os.environ['EMBERBSD_TEST_WORK']) as tmp:
            root = Path(tmp)
            old = root / 'old'
            expected = root / 'expected'
            old.mkdir()
            expected.mkdir()
            (old / 'archive.c').write_text('same\n')
            shutil.copy(old / 'archive.c', expected / 'archive.c')
            identity = {'api': 1, 'package': owner.PACKAGE,
                        'export_inputs_sha256': '1' * 64, 'upstream': '2' * 40,
                        'owner_sha256': '3' * 64}
            record = sourceprep.write_prepared_tree_receipt(old, package=owner.PACKAGE, identity=identity)
            current = {**identity, 'export_inputs_sha256': '4' * 64}
            def export(command, **kwargs):
                destination = Path(command[3]) / owner.PACKAGE / 'files'
                destination.parent.mkdir(parents=True)
                shutil.copytree(expected, destination)
            with patch.object(owner, 'selected_identity', return_value=current), \
                    patch.object(owner.subprocess, 'run', side_effect=export):
                self.assertEqual(record, owner.verify(old, '/sdk', '/git', '/patch'))
                (expected / 'archive.c').write_text('different\n')
                with self.assertRaisesRegex(ValueError, 'differs'):
                    owner.verify(old, '/sdk', '/git', '/patch')
                (old / 'archive.c').write_text('tampered\n')
                with self.assertRaises(SDKError):
                    owner.verify(old, '/sdk', '/git', '/patch')


if __name__ == '__main__':
    unittest.main()
