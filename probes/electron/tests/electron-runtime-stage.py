#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Exercise runtime staging with data fixtures. Do not run target programs."""

import argparse
import hashlib
import importlib.util
import os
from pathlib import Path
import stat
import struct
import sys
import tempfile
import unittest
import zipfile

sys.dont_write_bytecode = True


def elf_image(machine=62, kind=3):
    data = bytearray(64)
    data[:7] = b'\x7fELF\x02\x01\x01'
    struct.pack_into('<HHI', data, 16, kind, machine, 1)
    struct.pack_into('<H', data, 52, 64)
    return bytes(data)


class RuntimeStageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='electron-stage-test-')
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name).resolve()
        self.archive = self.work / 'dist.zip'
        self.output = self.work / 'payload'

    def write_archive(self, extra=(), *, image=None, omit=(), version=b'44.9.3\n'):
        entries = [('electron', elf_image() if image is None else image, stat.S_IFREG | 0o755),
                   ('LICENSE', b'Electron MIT notice\n', stat.S_IFREG | 0o644),
                   ('LICENSES.chromium.html', b'<html>Full generated notices</html>\n', stat.S_IFREG | 0o644),
                   ('version', version, stat.S_IFREG | 0o644), *extra]
        with zipfile.ZipFile(self.archive, 'w', compression=zipfile.ZIP_DEFLATED) as output:
            for name, value, mode in entries:
                if name in omit:
                    continue
                info = zipfile.ZipInfo(name)
                info.create_system = 3
                info.external_attr = mode << 16
                output.writestr(info, value, compress_type=zipfile.ZIP_DEFLATED)

    def stage(self, **kwargs):
        return controller.stage_runtime(self.archive, self.output,
            archive_sha256=hashlib.sha256(self.archive.read_bytes()).hexdigest(),
            target='amd64', sdk=sdk, **kwargs)

    def assert_refused(self):
        with self.assertRaises((ValueError, OSError, zipfile.BadZipFile, SDKError)):
            self.stage()
        self.assertFalse(os.path.lexists(self.output))
        self.assertEqual(list(self.work.glob('.electron-stage-*')), [])

    def test_preserves_current_bsd_runtime_members_and_notices(self):
        extras = [('resources/default_app.asar', b'asar bytes', stat.S_IFREG | 0o644),
                  ('locales/ru.pak', b'locale bytes', stat.S_IFREG | 0o644),
                  ('new-bsd-helper', elf_image(), stat.S_IFREG | 0o755),
                  ('libnew-runtime.so', elf_image(), stat.S_IFREG | 0o755)]
        self.write_archive(extras)
        facts = self.stage()
        self.assertEqual({row['path'] for row in facts['elf']},
                         {'electron', 'new-bsd-helper', 'libnew-runtime.so'})
        for name, value, mode in extras:
            self.assertEqual((self.output / name).read_bytes(), value)
            self.assertEqual(stat.S_IMODE((self.output / name).stat().st_mode), stat.S_IMODE(mode))
        self.assertEqual((self.output / 'LICENSES.chromium.html').read_bytes(),
                         b'<html>Full generated notices</html>\n')
        self.assertNotIn('status', facts)

    def test_contained_relative_link_is_preserved(self):
        self.write_archive([('resources/alias', b'../LICENSE', stat.S_IFLNK | 0o777)])
        self.stage()
        self.assertEqual(os.readlink(self.output / 'resources/alias'), '../LICENSE')

    def test_traversal_and_absolute_paths_are_refused(self):
        for name in ('../outside', '/outside', 'dir/../outside', 'a\\b', 'C:/outside'):
            with self.subTest(name=name):
                self.write_archive([(name, b'bad', stat.S_IFREG | 0o644)])
                self.assert_refused()
        self.assertFalse((self.work.parent / 'outside').exists())

    def test_aliases_and_parent_collisions_are_refused(self):
        for entries in (
                [('Electron', b'bad', stat.S_IFREG | 0o644)],
                [('./electron', b'bad', stat.S_IFREG | 0o644)],
                [('A/one', b'a', stat.S_IFREG | 0o644), ('a/two', b'b', stat.S_IFREG | 0o644)],
                [('file', b'a', stat.S_IFREG | 0o644), ('file/child', b'b', stat.S_IFREG | 0o644)]):
            with self.subTest(entries=entries):
                self.write_archive(entries)
                self.assert_refused()

    def test_link_escape_cycle_and_link_parent_are_refused(self):
        for entries in (
                [('bad', b'../outside', stat.S_IFLNK | 0o777)],
                [('a', b'b', stat.S_IFLNK | 0o777), ('b', b'a', stat.S_IFLNK | 0o777)],
                [('a', b'LICENSE', stat.S_IFLNK | 0o777), ('a/child', b'b', stat.S_IFREG | 0o644)],
                [('a', b'missing', stat.S_IFLNK | 0o777)],
                # Lexical normalization alone misses this escape through '..'.
                [('dir/back', b'..', stat.S_IFLNK | 0o777),
                 ('bad', b'dir/back/../outside', stat.S_IFLNK | 0o777)]):
            with self.subTest(entries=entries):
                self.write_archive(entries)
                self.assert_refused()

    def test_special_and_privilege_modes_are_refused(self):
        for mode in (stat.S_IFIFO | 0o644, stat.S_IFCHR | 0o644, stat.S_IFREG | 0o4755):
            with self.subTest(mode=mode):
                self.write_archive([('unsafe', b'', mode)])
                self.assert_refused()

    def test_missing_notices_wrong_version_and_host_executable_are_refused(self):
        for omitted in ('LICENSE', 'LICENSES.chromium.html', 'electron', 'version'):
            self.write_archive(omit=(omitted,))
            self.assert_refused()
        self.write_archive(version=b'44.5.1\n')
        self.assert_refused()
        self.write_archive(image=b'\xcf\xfa\xed\xfe' + b'\0' * 60)
        self.assert_refused()

    def test_wrong_cpu_class_and_object_are_refused(self):
        for image in (elf_image(183), elf_image(kind=1), b'\x7fELF'):
            with self.subTest(image=image):
                self.write_archive(image=image)
                self.assert_refused()

    def test_foreign_executable_helper_is_refused(self):
        self.write_archive([('bsd-helper', b'\xcf\xfa\xed\xfe' + b'\0' * 60,
                             stat.S_IFREG | 0o755)])
        self.assert_refused()

    def test_wrong_digest_is_refused_before_destination_creation(self):
        self.write_archive()
        with self.assertRaisesRegex(ValueError, 'SHA256 differs'):
            controller.stage_runtime(self.archive, self.output, archive_sha256='0' * 64,
                                     target='amd64', sdk=sdk)
        self.assertFalse(self.output.exists())

    def test_crc_corruption_is_refused_and_partial_output_removed(self):
        self.write_archive()
        with zipfile.ZipFile(self.archive) as archive:
            info = archive.getinfo('electron')
            offset = info.header_offset + 30 + len(info.filename.encode()) + len(info.extra)
        data = bytearray(self.archive.read_bytes())
        data[offset + 2] ^= 1
        self.archive.write_bytes(data)
        self.assert_refused()

    def test_existing_destination_and_archive_symlink_are_refused(self):
        self.write_archive()
        self.output.mkdir()
        (self.output / 'keep').write_bytes(b'unchanged')
        with self.assertRaisesRegex(ValueError, 'already exists'):
            self.stage()
        self.assertEqual((self.output / 'keep').read_bytes(), b'unchanged')
        (self.output / 'keep').unlink()
        self.output.rmdir()
        real = self.archive.with_suffix('.real')
        self.archive.rename(real)
        self.archive.symlink_to(real.name)
        self.assert_refused()

    def test_declared_size_limits_are_applied_before_extraction(self):
        self.write_archive()
        old = controller.MAX_TOTAL
        try:
            controller.MAX_TOTAL = 1
            self.assert_refused()
        finally:
            controller.MAX_TOTAL = old

    def test_central_directory_bound_is_checked_before_zipfile_allocation(self):
        self.write_archive()
        old = controller.MAX_CENTRAL_DIRECTORY
        try:
            controller.MAX_CENTRAL_DIRECTORY = 1
            self.assert_refused()
        finally:
            controller.MAX_CENTRAL_DIRECTORY = old

    def test_concurrent_destination_is_preserved(self):
        self.write_archive()
        publication = sdk[1]
        original = publication.publish_directory_noreplace

        def competing_writer(source, destination):
            destination.mkdir()
            (destination / 'keep').write_bytes(b'other owner')
            return original(source, destination)

        try:
            publication.publish_directory_noreplace = competing_writer
            with self.assertRaises(FileExistsError):
                self.stage()
        finally:
            publication.publish_directory_noreplace = original
        self.assertEqual((self.output / 'keep').read_bytes(), b'other owner')
        self.assertEqual(list(self.work.glob('.electron-stage-*')), [])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk-source', required=True)
    args, remaining = parser.parse_known_args()
    here = Path(__file__).resolve().parents[1]
    source = here / 'electron44/files/stage-runtime.py'
    spec = importlib.util.spec_from_file_location('electron_runtime_stage', source)
    controller = importlib.util.module_from_spec(spec)
    exec(compile(source.read_bytes(), str(source), 'exec'), controller.__dict__)
    sdk = controller.load_sdk(args.sdk_source)
    from emberbsd_sdk.errors import SDKError
    unittest.main(argv=[sys.argv[0], *remaining])
