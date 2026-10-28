#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted), GN source archive regression.
"""Check pinned GN content, archive normalization and refused unsafe inputs."""
import argparse
import hashlib
import importlib.util
import io
import os
from pathlib import Path
import re
import tarfile
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
RECIPE = ROOT / 'pkgsrc/devel/gn'
SPEC = importlib.util.spec_from_file_location('gn_source', RECIPE / 'files/fetch-source.py')
SOURCE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SOURCE)
SOURCE.load_sdk(['--sdk-source', os.environ['EMBERBSD_SDK_SOURCE']])
NORMALIZER = SOURCE.gitiles
ARCHIVES = []
# Independently produced by git write-tree from these two files/modes.
GOLDEN_TREE = '6311254086e4961bff7ee007b23c14b7e6fba2d2'
FILES = [('a.txt', 0o644, b'hello\n'), ('dir/b.sh', 0o755, b'#!/bin/sh\nexit 0\n')]


def archive(rows=FILES, *, mtime=123.5, extra=None):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode='w:gz', format=tarfile.PAX_FORMAT) as stream:
        for name, mode, data in rows:
            info = tarfile.TarInfo(name)
            info.mode, info.mtime, info.size = mode, mtime, len(data)
            info.uid, info.gid, info.uname, info.gname = 20, 30, 'ignored-user', 'ignored-group'
            stream.addfile(info, io.BytesIO(data))
        if extra is not None:
            stream.addfile(extra)
    return output.getvalue()


class GNSourceTests(unittest.TestCase):
    def refused(self, raw):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'source.tar'
            with self.assertRaises((NORMALIZER.SourceError, tarfile.TarError, EOFError)):
                SOURCE.publish(raw, GOLDEN_TREE, output)
            self.assertFalse(output.exists())
            self.assertEqual(list(Path(temporary).iterdir()), [])

    def test_git_tree_and_metadata_normalization(self):
        first, second = archive(), archive(list(reversed(FILES)), mtime=456.75)
        self.assertNotEqual(first, second)
        a = NORMALIZER.normalized_tar(NORMALIZER.read_gitiles(first, GOLDEN_TREE))
        b = NORMALIZER.normalized_tar(NORMALIZER.read_gitiles(second, GOLDEN_TREE))
        self.assertEqual(a, b)
        with tarfile.open(fileobj=io.BytesIO(a), mode='r:') as tar:
            self.assertEqual(tar.getnames(), ['a.txt', 'dir/b.sh'])
            for member, (name, mode, data) in zip(tar, FILES):
                self.assertEqual((member.name, member.mode, member.mtime), (name, mode, 0))
                self.assertEqual((member.uid, member.gid, member.uname, member.gname), (0, 0, '', ''))
                self.assertFalse(member.pax_headers)
                self.assertEqual(tar.extractfile(member).read(), data)

    def test_refuses_corrupted_blob(self):
        self.refused(archive([FILES[0], ('dir/b.sh', 0o755, b'changed\n')]))

    def test_refuses_changed_executable_bit(self):
        self.refused(archive([FILES[0], ('dir/b.sh', 0o644, FILES[1][2])]))

    def test_refuses_special_permission_bits(self):
        self.refused(archive([FILES[0], ('dir/b.sh', 0o4755, FILES[1][2])]))

    def test_refuses_duplicate_member(self):
        self.refused(archive(FILES + [FILES[0]]))

    def test_refuses_unsafe_paths(self):
        for name in ('/absolute', '../outside', 'dir/../../outside', 'dir//file', 'a/./b', 'dir\\file'):
            with self.subTest(name=name):
                self.refused(archive(FILES + [(name, 0o644, b'x')]))

    def test_refuses_case_colliding_parents(self):
        self.refused(archive(FILES + [('Dir/other', 0o644, b'x')]))

    def test_refuses_links_and_devices(self):
        for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.CHRTYPE, tarfile.FIFOTYPE):
            with self.subTest(kind=kind):
                member = tarfile.TarInfo('external')
                member.type, member.linkname = kind, '../../outside'
                self.refused(archive(extra=member))

    def test_refuses_untracked_empty_directory(self):
        member = tarfile.TarInfo('empty-directory')
        member.type = tarfile.DIRTYPE
        self.refused(archive(extra=member))

    def test_bounds_expanded_archive_and_source_content(self):
        with mock.patch.object(NORMALIZER, 'MAX_TAR', 512):
            self.refused(archive())
        with mock.patch.object(NORMALIZER, 'MAX_CONTENT', 8):
            self.refused(archive())

    def test_rejects_large_compressed_pax_before_metadata_parser(self):
        output = io.BytesIO()
        with tarfile.open(fileobj=output, mode='w:gz', format=tarfile.PAX_FORMAT) as stream:
            for name, mode, data in FILES:
                member = tarfile.TarInfo(name)
                member.mode, member.size = mode, len(data)
                member.pax_headers = {'comment': 'x' * (128 * 1024)}
                stream.addfile(member, io.BytesIO(data))
        raw = output.getvalue()
        self.assertLess(len(raw), 4096)
        with mock.patch.object(NORMALIZER, 'MAX_TAR', 64 * 1024), \
                mock.patch.object(NORMALIZER.tarfile, 'open', side_effect=AssertionError('metadata parser ran')):
            self.refused(raw)

    def test_refuses_truncated_archive(self):
        self.refused(archive()[:100])

    def test_refuses_missing_or_extra_blob(self):
        self.refused(archive(FILES[:1]))
        self.refused(archive(FILES + [('extra', 0o644, b'x')]))

    def test_publication_preserves_existing_files_and_symlinks(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'source.tar'
            SOURCE.publish(archive(), GOLDEN_TREE, output)
            original = output.read_bytes()
            with self.assertRaises((ValueError, NORMALIZER.SourceError)):
                SOURCE.publish(archive(), GOLDEN_TREE, output)
            self.assertEqual(output.read_bytes(), original)
            link = Path(temporary) / 'linked.tar'
            link.symlink_to(output)
            with self.assertRaises((ValueError, NORMALIZER.SourceError)):
                SOURCE.publish(archive(), GOLDEN_TREE, link)
            self.assertEqual(output.read_bytes(), original)

    def test_real_gitiles_inputs_produce_exact_distinfo(self):
        make = (RECIPE / 'Makefile').read_text()
        revision = re.search(r'^GN_REVISION=\s*([0-9a-f]{40})$', make, re.M).group(1)
        tree = re.search(r'^GN_TREE=\s*([0-9a-f]{40})$', make, re.M).group(1)
        self.assertEqual(revision, '641ace93dd9560e75e7add0d08f77b446fbb3b78')
        self.assertEqual(tree, '90329c7841d68716991cf2c247bcd9906c884c91')
        outputs, originals = [], []
        for path in ARCHIVES:
            raw = path.read_bytes(); originals.append(raw)
            files = NORMALIZER.read_gitiles(raw, tree)
            self.assertEqual(len(files), 1054)
            outputs.append(NORMALIZER.normalized_tar(files))
        self.assertGreaterEqual(len(set(originals)), 2, 'Provide two genuinely different Gitiles responses')
        self.assertEqual(len(set(outputs)), 1)
        info = (RECIPE / 'distinfo').read_text()
        name = 'gn-' + revision + '.tar'
        data = outputs[0]
        for label, algorithm in (('BLAKE2s', 'blake2s'), ('SHA512', 'sha512')):
            self.assertIn(f'{label} ({name}) = {hashlib.new(algorithm, data).hexdigest()}', info)
        self.assertIn(f'Size ({name}) = {len(data)} bytes', info)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gitiles-archive', action='append', type=Path, required=True)
    args, remaining = parser.parse_known_args()
    ARCHIVES = args.gitiles_archive
    unittest.main(argv=[__file__, *remaining])
