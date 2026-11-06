# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Verify the current libarchive recipe and prepared payload."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
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


class CurrentIdentityTest(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory(dir=os.environ['EMBERBSD_TEST_WORK'])
        self.addCleanup(self.work.cleanup)
        self.root = Path(self.work.name)
        self.source = self.root / 'prepared'
        self.source.mkdir()
        (self.source / 'source.c').write_text('payload\n')
        self.effective = {'api': 3, 'package': owner.PACKAGE,
                          'effective_package_sha256': '4' * 64, 'upstream': '1' * 40}
        self.identity = {'effective': self.effective, 'owner_sha256': '3' * 64}
        self.record = sourceprep.write_prepared_tree_receipt(
            self.source, package=owner.PACKAGE, identity=self.identity)

    def test_standalone_cli_loads_selected_sdk_without_pythonpath(self):
        result = subprocess.run(
            [sys.executable, '-I', '-S', '-B', str(ROOT / 'scripts/libarchive-source.py'),
             'verify', str(self.source), '--sdk-source', os.environ['EMBERBSD_SDK_SOURCE'],
             '--git', str(self.root / 'missing-git')],
            capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('git must be an absolute executable', result.stderr)
        self.assertNotIn('ModuleNotFoundError', result.stderr)

    def test_git_identity_receipt_needs_no_export(self):
        with patch.object(owner, 'selected_identity', return_value=self.identity), \
                patch.object(owner.subprocess, 'run') as run:
            self.assertEqual(self.record, owner.verify(self.source, '/sdk', '/git'))
            run.assert_not_called()
        changed = dict(self.identity, effective=dict(self.effective, effective_package_sha256='6' * 64))
        with patch.object(owner, 'selected_identity', return_value=changed):
            with self.assertRaisesRegex(ValueError, 'explicit patch'):
                owner.verify(self.source, '/sdk', '/git')

    def test_changed_recipe_compares_payload(self):
        export = self.root / 'export'
        files = export / owner.PACKAGE / 'files'
        files.mkdir(parents=True)
        (files / 'source.c').write_text('payload\n')
        changed = dict(self.identity, effective=dict(self.effective, effective_package_sha256='6' * 64))
        def do_export(command, **kwargs):
            shutil.copytree(export, Path(command[3]))
        with patch.object(owner, 'selected_identity', return_value=changed), \
                patch.object(owner.subprocess, 'run', side_effect=do_export):
            self.assertEqual(self.record, owner.verify(self.source, '/sdk', '/git', '/patch'))
            changed['owner_sha256'] = '5' * 64
            self.assertEqual(self.record, owner.verify(self.source, '/sdk', '/git', '/patch'))
            (files / 'source.c').write_text('changed payload\n')
            with self.assertRaisesRegex(ValueError, 'differs from current effective source'):
                owner.verify(self.source, '/sdk', '/git', '/patch')

    def test_preparation_has_one_identity_and_uses_shared_export(self):
        export = self.root / 'export'
        files = export / owner.PACKAGE / 'files'
        files.mkdir(parents=True)
        (files / 'source.c').write_text('payload\n')
        selector = owner.module(ROOT / 'scripts/pkgsrc-source-identity.py', 'test_selector')
        with patch.object(owner, 'selected_identity', return_value=self.identity), \
                patch.object(owner, 'module', return_value=selector), \
                patch.object(selector, 'shared_export', return_value=export) as shared, \
                patch.object(owner.subprocess, 'run') as run:
            record = owner.prepare(self.root / 'new', '/sdk', '/git', '/patch', '/shared')
            self.assertEqual(record['identity'], self.identity)
            sourceprep.validate_prepared_tree(self.root / 'new', package=owner.PACKAGE, identity=self.identity)
            shared.assert_called_once_with('/shared', owner.ROOT, '/git', '/sdk', '/patch')
            run.assert_not_called()

    def test_old_and_malformed_receipts_are_rejected(self):
        identities = [
            {'api': 1, 'package': owner.PACKAGE, 'export_inputs_sha256': '1' * 64,
             'upstream': '2' * 40, 'owner_sha256': '3' * 64},
            dict(self.identity, effective=dict(self.effective, api=1)),
            dict(self.identity, effective=dict(self.effective, api=2)),
            dict(self.identity, effective=dict(self.effective, legacy_api2_sha256='4' * 64)),
            dict(self.identity, effective=dict(self.effective, package='other/package')),
            dict(self.identity, owner_sha256='invalid'),
        ]
        for value in identities:
            with self.subTest(identity=value):
                (self.source / sourceprep.PREPARED_TREE_RECEIPT).unlink()
                sourceprep.write_prepared_tree_receipt(self.source, package=owner.PACKAGE, identity=value)
                with patch.object(owner, 'selected_identity', return_value=self.identity), \
                        patch.object(owner.subprocess, 'run') as run:
                    with self.assertRaisesRegex(SDKError, 'prepare the source again'):
                        owner.verify(self.source, '/sdk', '/git', '/patch')
                    run.assert_not_called()

    def test_current_identity_does_not_skip_payload_integrity(self):
        (self.source / 'source.c').write_text('tampered\n')
        with patch.object(owner, 'selected_identity', return_value=self.identity):
            with self.assertRaises(SDKError):
                owner.verify(self.source, '/sdk', '/git')

    def test_input_race_is_rejected(self):
        changed = dict(self.identity, effective=dict(self.effective, effective_package_sha256='6' * 64))
        with patch.object(owner, 'selected_identity', side_effect=[self.identity, changed]):
            with self.assertRaisesRegex(ValueError, 'inputs changed'):
                owner.verify(self.source, '/sdk', '/git')


if __name__ == '__main__':
    unittest.main()
