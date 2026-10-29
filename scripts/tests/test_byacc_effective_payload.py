# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Exercise effective-recipe fallback with a real archive and patch tool."""
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


class EffectivePayloadTest(unittest.TestCase):
    def test_recipe_metadata_and_actual_patch_output(self):
        with tempfile.TemporaryDirectory(dir=os.environ['EMBERBSD_TEST_WORK']) as tmp:
            root = Path(tmp)
            spec = importlib.util.spec_from_file_location('byacc_owner', ROOT / 'scripts/source-inputs/byacc/source.py')
            owner = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(owner)
            owner.load_sdk(['--sdk-source', os.environ['EMBERBSD_SDK_SOURCE']])
            archive = root / 'byacc-20260126.tgz'
            with tarfile.open(archive, 'w:gz') as tar:
                data = b'original\n'
                info = tarfile.TarInfo('byacc-20260126/main.c')
                info.size = len(data)
                info.mode = 0o644
                tar.addfile(info, io.BytesIO(data))
            recipe = root / 'recipe'
            recipe.mkdir()
            (recipe / 'Makefile').write_text('DISTNAME=\tbyacc-20260126\nCOMMENT=before\n')
            hashes = sourceprep.archive_hashes(archive.read_bytes())
            def write_distinfo(patch_data=None):
                text = (f'SHA512 ({archive.name}) = {hashes["sha512"]}\n'
                        f'BLAKE2s ({archive.name}) = {hashes["blake2s"]}\n'
                        f'Size ({archive.name}) = {hashes["size"]} bytes\n')
                if patch_data is not None:
                    text += f'SHA1 (patch-main) = {hashlib.sha1(patch_data).hexdigest()}\n'
                (recipe / 'distinfo').write_text(text)
            write_distinfo()
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
                # Stand in for the Git object ids of the fixture recipe.
                rows = sorted((path.relative_to(recipe).as_posix(), path.read_bytes().hex())
                              for path in recipe.rglob('*') if path.is_file())
                return {'api': 2, 'package': owner.PACKAGE, 'upstream': '1' * 40,
                        'effective_package_sha256': hashlib.sha256(repr(rows).encode()).hexdigest()}
            tool = os.environ['EMBERBSD_TEST_PATCH']
            git = os.environ['EMBERBSD_TEST_GIT']
            output = root / 'prepared'
            with patch.object(owner, 'source_identity', return_value=identity), \
                    patch.object(owner.process, 'capture', side_effect=capture), \
                    patch.object(owner, 'git_effective_identity', side_effect=git_identity):
                record = owner.prepare(str(archive), output, tool, git, True)
                self.assertEqual(record, owner.verify(output, git))
                (recipe / 'Makefile').write_text('DISTNAME=\tbyacc-20260126\nCOMMENT=after\n')
                self.assertEqual(record, owner.verify(output, git, str(archive), tool))
                delta = b'--- main.c\n+++ main.c\n@@ -1 +1 @@\n-original\n+changed\n'
                (recipe / 'patches').mkdir()
                (recipe / 'patches/patch-main').write_bytes(delta)
                write_distinfo(delta)
                with self.assertRaisesRegex(SDKError, 'differs from current'):
                    owner.verify(output, git, str(archive), tool)


if __name__ == '__main__':
    unittest.main()
