# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Check the legacy comparison boundary for the tar-based source owners."""
import importlib.util
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'pkgsrc/lang/llvm/files'))
sys.path.insert(0, str(Path(os.environ['EMBERBSD_SDK_SOURCE']) / 'src'))
from emberbsd_sdk import sourceprep
from emberbsd_sdk.errors import SDKError


class CompatibilityTest(unittest.TestCase):
    def test_scoped_owner_change_compares_payload(self):
        for name, package in (('byacc', 'devel/byacc'), ('libevent', 'devel/libevent')):
            with self.subTest(owner=name), tempfile.TemporaryDirectory(dir=os.environ['EMBERBSD_TEST_WORK']) as tmp:
                spec = importlib.util.spec_from_file_location('scoped_owner_' + name,
                    ROOT / 'scripts/source-inputs' / name / 'source.py')
                owner = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(owner)
                owner.load_sdk(['--sdk-source', os.environ['EMBERBSD_SDK_SOURCE']])
                root = Path(tmp)
                exported = root / 'export'
                recipe = exported / package
                recipe.mkdir(parents=True)
                (recipe / 'Makefile').write_text('recipe\n')
                selector = owner.identity_module()
                effective = selector.effective_package_identity(exported, package, '1' * 40)
                source = root / 'source'
                source.mkdir()
                (source / 'source.c').write_text('payload\n')
                old = {'effective': effective, 'owner_sha256': '3' * 64}
                record = sourceprep.write_prepared_tree_receipt(source, package=package, identity=old)
                current = {'export': {'upstream': '2' * 40}, 'owner_sha256': '4' * 64}
                def export(command, **kwargs):
                    shutil.copytree(exported, Path(command[3]))
                with patch.object(owner, 'source_identity', return_value=current), \
                        patch.object(owner.process, 'capture', side_effect=export), \
                        patch.object(owner, 'prepare', return_value={'tree_sha256': record['tree_sha256']}) as prepare:
                    self.assertEqual(owner.verify(source, '/git', '/archive', '/patch'), record)
                    prepare.return_value = {'tree_sha256': '0' * 64}
                    with self.assertRaisesRegex(SDKError, 'differs from current'):
                        owner.verify(source, '/git', '/archive', '/patch')
                    with self.assertRaisesRegex(SDKError, 'require an explicit archive'):
                        owner.verify(source, '/git', None, '/patch')
                    current['owner_sha256'] = old['owner_sha256']
                    (recipe / 'Makefile').write_text('recipe\nCOMMENT=changed\n')
                    prepare.return_value = {'tree_sha256': record['tree_sha256']}
                    self.assertEqual(owner.verify(source, '/git', '/archive', '/patch'), record)
                    (recipe / 'patches').mkdir()
                    (recipe / 'patches/patch-source').write_text('changed patch\n')
                    prepare.return_value = {'tree_sha256': '0' * 64}
                    with self.assertRaisesRegex(SDKError, 'differs from current'):
                        owner.verify(source, '/git', '/archive', '/patch')

    def test_archive_checksum_is_not_skipped(self):
        for name, package, dist, recipe_name in (
                ('byacc', 'devel/byacc', 'byacc-20260126', 'Makefile'),
                ('libevent', 'devel/libevent', 'libevent-2.1.13-stable', 'Makefile.common')):
            with self.subTest(owner=name), tempfile.TemporaryDirectory(dir=os.environ['EMBERBSD_TEST_WORK']) as tmp:
                spec = importlib.util.spec_from_file_location('archive_owner_' + name,
                    ROOT / 'scripts/source-inputs' / name / 'source.py')
                owner = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(owner)
                owner.load_sdk(['--sdk-source', os.environ['EMBERBSD_SDK_SOURCE']])
                root = Path(tmp)
                suffix = '.tgz' if name == 'byacc' else '.tar.gz'
                archive = root / (dist + suffix)
                archive.write_bytes(b'bad')
                recipe = root / 'recipe'
                recipe.mkdir()
                (recipe / 'Makefile').write_text('DISTNAME=\t' + dist + '\n')
                (recipe / recipe_name).write_text('DISTNAME=\t' + dist + '\n')
                (recipe / 'distinfo').write_text(
                    f'SHA512 ({archive.name}) = ' + '0' * 128 + '\n' +
                    f'BLAKE2s ({archive.name}) = ' + '0' * 64 + '\n' +
                    f'Size ({archive.name}) = 1 bytes\n')
                def export(command, **kwargs):
                    destination = Path(command[3]) / package
                    destination.parent.mkdir(parents=True)
                    shutil.copytree(recipe, destination)
                with patch.object(owner, 'source_identity', return_value={'example': 'identity'}), \
                        patch.object(owner.process, 'capture', side_effect=export):
                    with self.assertRaisesRegex(SDKError, 'archive checksum differs'):
                        owner.prepare(str(archive), root / 'output', '/patch', '/git')

    def test_legacy_compares_current_payload_and_archive(self):
        for name, package in (('byacc', 'devel/byacc'), ('libevent', 'devel/libevent')):
            with self.subTest(owner=name), tempfile.TemporaryDirectory(dir=os.environ['EMBERBSD_TEST_WORK']) as tmp:
                spec = importlib.util.spec_from_file_location('owner_' + name,
                    ROOT / 'scripts/source-inputs' / name / 'source.py')
                owner = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(owner)
                owner.load_sdk(['--sdk-source', os.environ['EMBERBSD_SDK_SOURCE']])
                source = Path(tmp) / 'source'
                source.mkdir()
                (source / 'source.c').write_text('payload\n')
                old = {'export': {'api': 1, 'package': package,
                                  'export_inputs_sha256': '1' * 64, 'upstream': '2' * 40},
                       'owner_sha256': '3' * 64}
                record = sourceprep.write_prepared_tree_receipt(source, package=package, identity=old)
                current = {'export': {**old['export'], 'export_inputs_sha256': '4' * 64},
                           'owner_sha256': '3' * 64}
                with patch.object(owner, 'source_identity', return_value=current), \
                        patch.object(owner, 'prepare', return_value={'tree_sha256': record['tree_sha256']}) as prepare:
                    self.assertEqual(owner.verify(source, '/git', '/archive', '/patch'), record)
                    self.assertEqual(prepare.call_args.args[0], '/archive')
                    prepare.return_value = {'tree_sha256': '0' * 64}
                    with self.assertRaisesRegex(SDKError, 'differs from current'):
                        owner.verify(source, '/git', '/archive', '/patch')
                    with self.assertRaisesRegex(SDKError, 'explicit archive and patch'):
                        owner.verify(source, '/git')
                    (source / 'source.c').write_text('tampered\n')
                    with self.assertRaises(SDKError):
                        owner.verify(source, '/git', '/archive', '/patch')


if __name__ == '__main__':
    unittest.main()
