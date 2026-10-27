#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Exercise ordered source application and all-before-write materialization."""
import argparse
import difflib
import importlib.util
import json
from pathlib import Path
import unittest


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def delta(before, after, name):
    return ''.join(difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True),
                                      fromfile='a/' + name if before else '/dev/null', tofile='b/' + name))


class BuildSources(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.OverlayAudit()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.patch_root = self.root / 'ports-patches'
        self.patch_root.mkdir()
        (self.patch_root / 'first.patch').write_text(delta('BSD support\n', 'BSD support\nfirst\n', 'alpha.cc'))
        (self.patch_root / 'second.patch').write_text(
            delta('BSD support\nfirst\n', 'BSD support\nfirst\nsecond\n', 'alpha.cc') +
            delta('', 'new Ports source\n', 'ports.cc'))
        self.manifest = self.root / 'source-series.json'
        self.series = dict(version=1, stage='after-pinned-electron-upstream-and-bsd-patches', patches=[
            dict(path=name, root='', strip=1) for name in ('first.patch', 'second.patch')])
        self.write_series()

    def write_series(self):
        self.manifest.write_text(json.dumps(self.series))

    def prepare(self):
        f = self.fixture
        return helper.prepare(f.workspace, f.pkgsrc, f.archive, f.destination,
                              options.git, options.patch, self.patch_root, self.manifest)

    def test_real_ordered_patches_then_idempotent_materialization(self):
        result = self.prepare()
        self.assertEqual((self.fixture.src / 'alpha.cc').read_text(), 'Electron upstream\n')
        self.assertEqual([row['path'] for row in result['patches']], ['first.patch', 'second.patch'])
        self.assertEqual(helper.materialize(self.fixture.workspace, self.fixture.destination, result, git=options.git), 4)
        self.assertEqual((self.fixture.src / 'alpha.cc').read_text(), 'BSD support\nfirst\nsecond\n')
        self.assertEqual((self.fixture.src / 'ports.cc').read_text(), 'new Ports source\n')
        self.assertEqual(helper.materialize(self.fixture.workspace, self.fixture.destination, result, git=options.git), 0)

    def test_wrong_order_fails_without_source_mutation(self):
        self.series['patches'].reverse(); self.write_series()
        with self.assertRaisesRegex(ValueError, 'ordered source patch failed'):
            self.prepare()
        self.assertEqual((self.fixture.src / 'alpha.cc').read_text(), 'Electron upstream\n')
        self.assertFalse((self.fixture.destination / 'prepared-sources.json').exists())

    def test_last_conflicting_source_refused_before_first_write(self):
        result = self.prepare()
        (self.fixture.src / 'ports.cc').write_text('unrelated caller input\n')
        with self.assertRaisesRegex(ValueError, 'source differs'):
            helper.materialize(self.fixture.workspace, self.fixture.destination, result, git=options.git)
        self.assertEqual((self.fixture.src / 'alpha.cc').read_text(), 'Electron upstream\n')
        self.assertFalse((self.fixture.src / 'new.cc').exists())
        self.assertEqual((self.fixture.src / 'ports.cc').read_text(), 'unrelated caller input\n')

    def test_modified_prepared_bytes_refused(self):
        result = self.prepare()
        (self.fixture.destination / 'files/ports.cc').write_text('changed\n')
        with self.assertRaisesRegex(ValueError, 'prepared source changed'):
            helper.materialize(self.fixture.workspace, self.fixture.destination, result, git=options.git)
        self.assertEqual((self.fixture.src / 'alpha.cc').read_text(), 'Electron upstream\n')

    def test_source_symlink_refused_without_following(self):
        result = self.prepare()
        outside = self.root / 'outside'; outside.write_text('outside\n')
        (self.fixture.src / 'ports.cc').symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            helper.materialize(self.fixture.workspace, self.fixture.destination, result, git=options.git)
        self.assertEqual(outside.read_text(), 'outside\n')
        self.assertEqual((self.fixture.src / 'alpha.cc').read_text(), 'Electron upstream\n')

    def test_source_revision_mismatch_refused(self):
        result = self.prepare()
        self.fixture.git(self.fixture.src, 'commit', '--allow-empty', '-qm', 'different pin')
        with self.assertRaisesRegex(ValueError, 'HEAD differs'):
            helper.materialize(self.fixture.workspace, self.fixture.destination, result, git=options.git)
        self.assertEqual((self.fixture.src / 'alpha.cc').read_text(), 'Electron upstream\n')

    def test_duplicate_and_traversal_series_refused(self):
        for field, value in (('path', '../first.patch'), ('root', '../outside'), ('strip', True)):
            original = self.series['patches'][0][field]
            self.series['patches'][0][field] = value; self.write_series()
            with self.assertRaises(ValueError):
                helper.read_series(self.manifest, self.patch_root)
            self.series['patches'][0][field] = original
        self.series['patches'].append(self.series['patches'][0]); self.write_series()
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            helper.read_series(self.manifest, self.patch_root)

    def test_rename_patch_refused(self):
        filename = self.patch_root / 'first.patch'
        filename.write_text(filename.read_text().replace('+++ b/alpha.cc', '+++ b/elsewhere.cc'))
        with self.assertRaisesRegex(ValueError, 'renames'):
            helper.read_series(self.manifest, self.patch_root)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--git', type=Path, required=True)
    parser.add_argument('--patch', type=Path, required=True)
    options, remaining = parser.parse_known_args()
    directory = Path(__file__).resolve().parent
    helper = load('electron_build_sources', directory.parent / 'electron44/files/prepare-build-sources.py')
    fixtures = load('electron_bsd_fixtures', directory / 'electron-bsd-overlay.py')
    fixtures.helper = helper.bsd
    fixtures.options = options
    unittest.main(argv=[__file__, *remaining])
