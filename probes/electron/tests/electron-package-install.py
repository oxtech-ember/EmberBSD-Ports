#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Exercise package installation without compilers or target execution."""
import argparse
import importlib.util
import os
from pathlib import Path
import stat
import struct
import tempfile
import unittest
import zipfile
from unittest.mock import patch


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='electron package ')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.work = self.root/'producer'; (self.work/'out').mkdir(parents=True)
        self.dest = self.root/'dest'; self.dest.mkdir()
        self.runtime = self.dest/'usr/pkg/lib/electron44'
        image = bytearray(64); image[:7] = b'\x7fELF\x02\x01\x01'
        struct.pack_into('<HHI', image, 16, 3, 62, 1)
        struct.pack_into('<H', image, 52, 64)
        self.members = [('electron', bytes(image), stat.S_IFREG|0o755),
            ('LICENSE', b'MIT notice', stat.S_IFREG|0o644),
            ('LICENSES.chromium.html', b'<html>notices</html>', stat.S_IFREG|0o644),
            ('version', b'45.2.1\n', stat.S_IFREG|0o644),
            ('resources/new asset', b'preserve all members', stat.S_IFREG|0o644),
            ('resources/alias', b'../LICENSE', stat.S_IFLNK|0o777),
            ('empty/', b'', stat.S_IFDIR|0o755)]
        with zipfile.ZipFile(self.work/'out/dist.zip', 'w') as archive:
            for name, data, mode in self.members:
                item = zipfile.ZipInfo(name); item.create_system = 3
                item.external_attr = mode << 16
                archive.writestr(item, data)

    def install(self, **kw):
        options = dict(work=self.work, destdir=self.dest, prefix='/usr/pkg',
                       target='amd64', sdk=sdk, owner=owner)
        options.update(kw)
        return installer.install(**options)

    def test_complete_payload_link_and_plist(self):
        with patch.object(owner.hashlib, 'file_digest', wraps=owner.hashlib.file_digest) as digest:
            facts = self.install()
            self.assertEqual(digest.call_count, 1)
        self.assertEqual(len(facts['members']), len(self.members))
        self.assertEqual((self.runtime/'resources/new asset').read_bytes(), b'preserve all members')
        self.assertEqual(os.readlink(self.dest/'usr/pkg/bin/electron'), '../lib/electron44/electron')
        self.assertEqual(os.readlink(self.runtime/'resources/alias'), '../LICENSE')
        self.assertEqual(installer.plist(self.dest, '/usr/pkg'), sorted([
            'bin/electron', '@pkgdir lib/electron44/empty',
            *['lib/electron44/'+name for name, _, mode in self.members if not stat.S_ISDIR(mode)]]))

    def test_existing_runtime_and_link_preserved(self):
        self.install()
        with self.assertRaises(ValueError): self.install()
        self.assertEqual((self.runtime/'LICENSE').read_bytes(), b'MIT notice')

    def test_foreign_link_name_refused_before_extract(self):
        binary = self.dest/'usr/pkg/bin/electron'; binary.parent.mkdir(parents=True)
        binary.write_text('foreign')
        with self.assertRaises(ValueError): self.install()
        self.assertEqual(binary.read_text(), 'foreign')
        self.assertFalse(self.runtime.exists())

    def test_redirected_parent_refused(self):
        outside = self.root/'outside'; outside.mkdir()
        (self.dest/'usr').symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError): self.install()
        with self.assertRaises(ValueError): installer.plist(self.dest, '/usr/pkg')
        self.assertEqual(list(outside.iterdir()), [])

    def test_bad_prefix_overlap_and_target_refused(self):
        with self.assertRaises(ValueError): self.install(prefix='/other')
        with self.assertRaises(SDKError): self.install(destdir=self.work)
        with self.assertRaises(SDKError): self.install(target='aarch64')
        self.assertFalse(self.runtime.exists())

    def test_link_race_leaves_foreign_entry_and_owned_payload(self):
        real_symlink = os.symlink
        def race(target, path, **kwargs):
            if Path(path).name == 'electron':
                Path(path).write_text('concurrent')
                raise FileExistsError(path)
            return real_symlink(target, path, **kwargs)
        with patch.object(installer.os, 'symlink', side_effect=race):
            with self.assertRaises(FileExistsError): self.install()
        self.assertEqual((self.dest/'usr/pkg/bin/electron').read_text(), 'concurrent')
        self.assertTrue(self.runtime.is_dir())

    def test_plist_propagates_walk_error(self):
        self.install()
        def denied(path, *, followlinks, onerror):
            onerror(PermissionError('denied'))
            return iter(())
        with patch.object(installer.os, 'walk', side_effect=denied):
            with self.assertRaises(PermissionError): installer.plist(self.dest, '/usr/pkg')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--sdk-source', required=True)
    args = parser.parse_args()
    files = Path(__file__).resolve().parents[1]/'electron44/files'
    installer = load(files/'install-runtime.py', 'electron_install')
    owner = installer.stage_owner(); sdk = owner.load_sdk(args.sdk_source)
    from emberbsd_sdk.errors import SDKError
    unittest.main(argv=[__file__])
