# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Exercise network source recipes with the real shared archive preparer."""
import hashlib
import importlib.util
import io
import os
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SDK = Path(os.environ['EMBERBSD_SDK_SOURCE'])
WORK = Path(os.environ['EMBERBSD_TEST_WORK'])
sys.path.insert(0, str(SDK / 'src'))
from emberbsd_sdk.errors import SDKError


class NetworkSourcesTest(unittest.TestCase):
    def test_libpcap_pre_extraction_receipt_is_still_accepted(self):
        spec = importlib.util.spec_from_file_location('libpcap_owner', ROOT / 'scripts/source-inputs/libpcap/source.py')
        owner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(owner)
        owner.load_sdk(['--sdk-source', str(SDK)])
        with tempfile.TemporaryDirectory(dir=WORK) as temp:
            from emberbsd_sdk import sourceprep
            old_digest = next(iter(owner.compatible_owner_digests))
            effective = {'api': 2, 'package': owner.PACKAGE,
                         'effective_package_sha256': 'a' * 64, 'upstream': 'b' * 40}
            old = {'effective': effective, 'owner_sha256': old_digest}
            record = sourceprep.write_prepared_tree_receipt(temp, package=owner.PACKAGE, identity=old)
            selector = owner.identity_module()
            with patch.object(owner, 'source_identity', return_value={'export': {'current': True}, 'owner_sha256': 'c' * 64}), \
                    patch.object(owner, 'identity_module', return_value=selector), \
                    patch.object(owner, 'git_effective_identity', return_value=effective):
                self.assertEqual(owner.verify(temp, '/bin/true'), record)

    def test_recipe_archive_receipt_and_patch_inventory(self):
        for name, package in (('mdns', 'net/mDNSResponder'), ('dhcpcd', 'net/dhcpcd')):
            with self.subTest(name=name), tempfile.TemporaryDirectory(dir=WORK) as temp:
                spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts/source-inputs' / name / 'source.py')
                owner = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(owner)
                owner.engine.load_sdk(['--sdk-source', str(SDK)])
                root = Path(temp)
                recipe = root / 'export' / package
                recipe.mkdir(parents=True)
                upstream = ROOT / 'pkgsrc' / package
                for filename in ('Makefile', 'Makefile.common'):
                    (recipe / filename).write_bytes((upstream / filename).read_bytes())
                version = '2881.120.11' if name == 'mdns' else '10.5.2'
                distname = ('mDNSResponder-' if name == 'mdns' else 'dhcpcd-') + version
                archive = root / (distname + ('.tar.gz' if name == 'mdns' else '.tar.xz'))
                archive_root = ('mDNSResponder-' if name == 'mdns' else '') + distname
                with tarfile.open(archive, 'w:gz' if name == 'mdns' else 'w:xz') as output:
                    entry = tarfile.TarInfo(archive_root + '/input.c')
                    entry.size = 7
                    output.addfile(entry, io.BytesIO(b'input;\n'))
                data = archive.read_bytes()
                (recipe / 'distinfo').write_text(
                    f'BLAKE2s ({archive.name}) = {hashlib.blake2s(data).hexdigest()}\n'
                    f'SHA512 ({archive.name}) = {hashlib.sha512(data).hexdigest()}\n'
                    f'Size ({archive.name}) = {len(data)} bytes\n')
                metadata, patches = owner.recipe(root / 'export')
                self.assertEqual(metadata['archive_root'], archive_root)
                self.assertEqual(patches, [])
                common = recipe / 'Makefile.common'
                original = common.read_text()
                keys = ('DISTNAME', 'GITHUB_TAG', 'GITHUB_PROJECT', 'WRKSRC', 'DISTFILES') if name == 'mdns' else (
                    'GITHUB_PROJECT', 'DISTNAME', 'GITHUB_RELEASE', 'EXTRACT_SUFX', 'WRKSRC', 'DISTFILES')
                for key in keys:
                    with self.subTest(name=name, selector=key):
                        common.write_text(original + '\n' + key + '=unexpected\n')
                        with self.assertRaisesRegex(SDKError, 'source selection'):
                            owner.recipe(root / 'export')
                common.write_text(original)
                identity = {'export': {'package': package}, 'owner_sha256': owner.owner_digest()}
                with patch.object(owner.engine, 'source_identity', return_value=identity):
                    out = root / 'prepared'
                    receipt = owner.engine.prepare(str(archive), str(out), '/bin/true', '/bin/true',
                                                   exported=root / 'export')
                    self.assertEqual(receipt['package'], package)
                    self.assertEqual(owner.engine.verify(str(out), '/bin/true'), receipt)
                    (out / 'input.c').write_text('changed\n')
                    with self.assertRaises(SDKError):
                        owner.engine.verify(str(out), '/bin/true')
                (recipe / 'patches').mkdir()
                (recipe / 'patches/patch-unlisted').write_text('unexpected')
                with self.assertRaisesRegex(SDKError, 'patch inventory'):
                    owner.recipe(root / 'export')


if __name__ == '__main__':
    unittest.main()
