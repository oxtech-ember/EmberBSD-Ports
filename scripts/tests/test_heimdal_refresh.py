# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Refresh an actual prepared Heimdal fixture against changed recipe inputs."""
import hashlib
import importlib.util
import io
import os
from pathlib import Path
import shutil
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'pkgsrc/lang/llvm/files'))
sys.path.insert(0, str(Path(os.environ['EMBERBSD_SDK_SOURCE']) / 'src'))
from emberbsd_sdk import sourceprep
from emberbsd_sdk.errors import SDKError


class RefreshTest(unittest.TestCase):
    def test_metadata_refresh_and_rejection(self):
        with tempfile.TemporaryDirectory(dir=os.environ['EMBERBSD_TEST_WORK']) as tmp:
            root = Path(tmp)
            spec = importlib.util.spec_from_file_location('heimdal_owner', ROOT / 'scripts/source-inputs/heimdal/source.py')
            owner = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(owner)
            owner.load_sdk(['--sdk-source', os.environ['EMBERBSD_SDK_SOURCE']])
            archive = root / 'heimdal-7.8.0.tar.gz'
            with tarfile.open(archive, 'w:gz') as tar:
                for name, data in [('lib/hcrypto/heim_find_prime.h', b'old header\n'), ('main.c', b'original\n')]:
                    info = tarfile.TarInfo('heimdal-7.8.0/' + name)
                    info.size = len(data)
                    info.mode = 0o644
                    tar.addfile(info, io.BytesIO(data))
            recipe = root / 'recipe'
            (recipe / 'files').mkdir(parents=True)
            (recipe / 'patches').mkdir()
            (recipe / 'files/heim_find_prime.h').write_text('header\n')
            (recipe / 'Makefile').write_text('DISTNAME=\theimdal-7.8.0\nCOMMENT=before\n')
            hashes = sourceprep.archive_hashes(archive.read_bytes())
            def distinfo(delta=None):
                text = (f'SHA512 ({archive.name}) = {hashes["sha512"]}\n'
                        f'BLAKE2s ({archive.name}) = {hashes["blake2s"]}\n'
                        f'Size ({archive.name}) = {hashes["size"]} bytes\n')
                if delta:
                    text += f'SHA1 (patch-main) = {hashlib.sha1(delta).hexdigest()}\n'
                (recipe / 'distinfo').write_text(text)
            distinfo()
            identity = {'export': {'upstream': '1' * 40}, 'owner_sha256': '3' * 64}
            real_capture = owner.process.capture
            def capture(command, **kwargs):
                if len(command) > 3 and str(command[2]).endswith('prepare-pkgsrc.py'):
                    destination = Path(command[3]) / owner.PACKAGE
                    destination.parent.mkdir(parents=True)
                    shutil.copytree(recipe, destination)
                    return None
                return real_capture(command, **kwargs)
            def git_identity(git):
                rows = sorted((p.relative_to(recipe).as_posix(), p.read_bytes().hex())
                              for p in recipe.rglob('*') if p.is_file())
                return {'api': 2, 'package': owner.PACKAGE, 'upstream': '1' * 40,
                        'effective_package_sha256': hashlib.sha256(repr(rows).encode()).hexdigest()}
            tool, git = os.environ['EMBERBSD_TEST_PATCH'], os.environ['EMBERBSD_TEST_GIT']
            output = root / 'prepared'
            receipt = output / sourceprep.PREPARED_TREE_RECEIPT
            with patch.object(owner, 'source_identity', return_value=identity), \
                    patch.object(owner.process, 'capture', side_effect=capture), \
                    patch.object(owner, 'git_effective_identity', side_effect=git_identity):
                original = owner.prepare(str(archive), output, tool, git)
                (recipe / 'Makefile').write_text('DISTNAME=\theimdal-7.8.0\nCOMMENT=after\n')
                real_verify = owner.verify
                def verified(*args, **kwargs):
                    result = real_verify(*args, **kwargs)
                    # A second tree validation/hash after verify is forbidden.
                    owner.sourceprep.validate_prepared_tree = lambda *a, **k: self.fail('second tree validation')
                    return result
                original_validate = owner.sourceprep.validate_prepared_tree
                try:
                    with patch.object(owner, 'verify', side_effect=verified):
                        refreshed = owner.refresh(output, git, str(archive), tool)
                finally:
                    owner.sourceprep.validate_prepared_tree = original_validate
                self.assertEqual(refreshed['tree_sha256'], original['tree_sha256'])
                self.assertEqual(refreshed['identity']['effective'], git_identity(git))
                self.assertTrue(owner.identity_module().current_git_package(
                    refreshed['identity'], identity['owner_sha256'], lambda: git_identity(git)))
                self.assertEqual(owner.verify(output, git), refreshed)
                prior = receipt.read_bytes()
                # Refuse a recipe change between verification and publication.
                calls = iter((identity, dict(identity, owner_sha256='4' * 64)))
                with patch.object(owner, 'source_identity', side_effect=lambda git: next(calls)), \
                        patch.object(owner, 'verify', return_value=refreshed):
                    with self.assertRaisesRegex(SDKError, 'inputs changed'):
                        owner.refresh(output, git, str(archive), tool)
                self.assertEqual(receipt.read_bytes(), prior)
                # Never overwrite a receipt concurrently replaced during verification.
                def replace_receipt(*args, **kwargs):
                    changed = dict(refreshed, tree_sha256='5' * 64)
                    receipt.write_bytes(owner.jsonio.json_bytes(changed))
                    return refreshed
                with patch.object(owner, 'verify', side_effect=replace_receipt):
                    with self.assertRaisesRegex(SDKError, 'receipt changed'):
                        owner.refresh(output, git, str(archive), tool)
                self.assertNotEqual(receipt.read_bytes(), prior)
                receipt.write_bytes(prior)
                delta = b'--- main.c\n+++ main.c\n@@ -1 +1 @@\n-original\n+changed\n'
                (recipe / 'patches/patch-main').write_bytes(delta)
                distinfo(delta)
                with self.assertRaisesRegex(SDKError, 'differs from current'):
                    owner.refresh(output, git, str(archive), tool)
                self.assertEqual(receipt.read_bytes(), prior)
                (output / 'main.c').write_text('tampered\n')
                with self.assertRaises(SDKError):
                    owner.refresh(output, git, str(archive), tool)
                self.assertEqual(receipt.read_bytes(), prior)
                with patch.object(owner, 'verify', side_effect=SDKError('failure')):
                    with self.assertRaisesRegex(SDKError, 'failure'):
                        owner.refresh(output, git, str(archive), tool)
                self.assertEqual(receipt.read_bytes(), prior)


    def test_tdb_owner_refresh_route(self):
        with tempfile.TemporaryDirectory(dir=os.environ['EMBERBSD_TEST_WORK']) as tmp:
            spec = importlib.util.spec_from_file_location('tdb_owner', ROOT / 'scripts/source-inputs/tdb/source.py')
            owner = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(owner)
            owner.load_sdk(['--sdk-source', os.environ['EMBERBSD_SDK_SOURCE']])
            root = Path(tmp)
            (root / 'payload').write_text('unchanged')
            old = {'effective': {'old': True}, 'owner_sha256': '1' * 64}
            record = sourceprep.write_prepared_tree_receipt(root, package=owner.PACKAGE, identity=old)
            current = {'api': 2, 'package': owner.PACKAGE, 'upstream': '2' * 40,
                       'effective_package_sha256': '3' * 64}
            state = {'export': {}, 'owner_sha256': '4' * 64}
            with patch.object(owner, 'source_identity', return_value=state), \
                    patch.object(owner, 'git_effective_identity', return_value=current), \
                    patch.object(owner, 'verify', return_value=record) as verifier:
                updated = owner.refresh(root, '/git', '/archive', '/patch', pkgsrc_export='/export')
            verifier.assert_called_once_with(root, '/git', '/archive', '/patch', pkgsrc_export='/export')
            self.assertEqual(updated['identity'], {'effective': current, 'owner_sha256': '4' * 64})
            self.assertEqual(updated['tree_sha256'], record['tree_sha256'])
            self.assertEqual((root / 'payload').read_text(), 'unchanged')


if __name__ == '__main__':
    unittest.main()
