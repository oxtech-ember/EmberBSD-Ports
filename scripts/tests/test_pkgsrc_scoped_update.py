#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Real-Git, source-only tests for the shared pkgsrc scoped updater.

Run after implementation with PORTS_ROOT, EMBERBSD_SDK_SOURCE, EXPORT_TEST_GIT,
EXPORT_TEST_PATCH and a Python supporting tarfile filters. Never uses a live tree.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

PORTS = Path(os.environ['PORTS_ROOT']).resolve()
SDK = Path(os.environ['EMBERBSD_SDK_SOURCE']).resolve()
GIT = os.environ['EXPORT_TEST_GIT']
PATCH = os.environ['EXPORT_TEST_PATCH']


def run(argv, cwd, *, check=True):
    return subprocess.run([str(x) for x in argv], cwd=cwd, text=True,
                          capture_output=True, check=check,
                          env=dict(os.environ, LC_ALL='C', GIT_CONFIG_NOSYSTEM='1',
                                   GIT_OPTIONAL_LOCKS='0', GIT_NO_LAZY_FETCH='1'))


def write(root, name, data):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data)
    return path


def init_git(root):
    root.mkdir(parents=True, exist_ok=True)
    run([GIT, 'init', '-q'], root)
    run([GIT, 'config', 'user.name', 'Fixture'], root)
    run([GIT, 'config', 'user.email', 'fixture@example.invalid'], root)


def commit(root, message):
    run([GIT, 'add', '-A'], root)
    run([GIT, 'commit', '-qm', message], root)


class ScopedUpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='pkgsrc-update-test-')
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name).resolve()
        self.ports = self.work / 'ports'
        init_git(self.ports)
        upstream = self.ports / 'upstream/pkgsrc'
        init_git(upstream)
        for category in ('cat', 'net'):
            write(upstream, category + '/Makefile', '.include "../mk/misc/category.mk"\n')
        write(upstream, 'cat/pkg/Makefile', 'PKGNAME=fixture-1\n')
        write(upstream, 'cat/pkg/files/unchanged', 'unchanged\n')
        write(upstream, 'cat/pkg/files/deleted', 'delete-me\n')
        write(upstream, 'cat/other/Makefile', 'PKGNAME=other-1\n')
        write(upstream, 'net/libfetch/Makefile', 'PKGNAME=libfetch-1\n')
        write(upstream, 'net/libfetch/files/source', 'unchanged\n')
        commit(upstream, 'upstream')
        (self.ports / 'scripts').mkdir()
        # The updater can add support modules without this test duplicating them.
        for source in (PORTS / 'scripts').glob('pkgsrc*.py'):
            shutil.copy2(source, self.ports / 'scripts' / source.name)
        shutil.copy2(PORTS / 'scripts/prepare-pkgsrc.py', self.ports / 'scripts')
        loader = self.ports / 'pkgsrc/lang/llvm/files/sdk_source.py'
        loader.parent.mkdir(parents=True)
        shutil.copy2(PORTS / 'pkgsrc/lang/llvm/files/sdk_source.py', loader)
        write(self.ports, 'pkgsrc/lang/llvm/Makefile', 'PKGNAME=llvm-1\n')
        write(self.ports, 'resources/owner.txt', 'old-owner\n')
        write(self.ports, 'pkgsrc/export.conf', 'file\tresources/owner.txt\tmisc/owner.txt\n')
        # git add records this independently initialized checkout as a gitlink.
        commit(self.ports, 'old input')
        self.export = self.work / 'shared'
        self.command = [sys.executable, '-B', self.ports / 'scripts/pkgsrc-shared-export.py',
                        self.export, '--sdk-source', SDK, '--git', GIT, '--patch', PATCH]
        result = run(self.command, self.ports, check=False)
        if result.returncode:
            self.fail('initial shared export failed: ' + result.stdout + result.stderr)
        self.tree = self.export / 'pkgsrc'
        self.receipt = self.export / 'pkgsrc-export.json'
        self.old_receipt = self.receipt.read_bytes()
        self.marker = self.export / '.pkgsrc-update-incomplete'

    def newer_inputs(self):
        patch = ('--- a/cat/pkg/Makefile\n+++ b/cat/pkg/Makefile\n'
                 '@@ -1 +1 @@\n-PKGNAME=fixture-1\n+PKGNAME=fixture-2\n'
                 '--- a/cat/pkg/files/deleted\n+++ /dev/null\n'
                 '@@ -1 +0,0 @@\n-delete-me\n')
        write(self.ports, 'patches/fixture.patch', patch)
        write(self.ports, 'resources/owner.txt', 'new-owner\n')
        write(self.ports, 'pkgsrc/export.conf',
              'patch\tpatches/fixture.patch\nfile\tresources/owner.txt\tmisc/owner.txt\n')
        commit(self.ports, 'update selected outputs')

    def update(self, *extra):
        return run(self.command + ['--update', '--package', 'cat/pkg', '--file', 'misc/owner.txt', *extra],
                   self.ports, check=False)

    def assert_refused_unchanged(self, result):
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.receipt.read_bytes(), self.old_receipt)
        self.assertEqual((self.tree / 'cat/pkg/Makefile').read_text(), 'PKGNAME=fixture-1\n')
        self.assertEqual((self.tree / 'misc/owner.txt').read_text(), 'old-owner\n')

    def test_changed_patch_and_file_preserve_unrelated_times_and_delete(self):
        unchanged = self.tree / 'cat/pkg/files/unchanged'
        other = self.tree / 'cat/other/Makefile'
        for path in (unchanged, other):
            os.utime(path, ns=(1_234_567_890_000_000_000,) * 2)
        before = {path: (path.stat().st_mtime_ns, path.stat().st_ino) for path in (unchanged, other)}
        self.newer_inputs()
        result = self.update()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.tree / 'cat/pkg/Makefile').read_text(), 'PKGNAME=fixture-2\n')
        self.assertEqual((self.tree / 'misc/owner.txt').read_text(), 'new-owner\n')
        self.assertFalse((self.tree / 'cat/pkg/files/deleted').exists())
        self.assertFalse(self.marker.exists())
        self.assertNotEqual(self.receipt.read_bytes(), self.old_receipt)
        self.assertEqual({path: (path.stat().st_mtime_ns, path.stat().st_ino)
                          for path in before}, before)

    def test_interrupted_write_leaves_marker_and_old_receipt(self):
        self.newer_inputs()
        code = r"""import importlib.util,sys
from unittest.mock import patch
s=importlib.util.spec_from_file_location('u',sys.argv[1]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
replace=m.os.replace
calls=[0]
def fail_after_one(*args):
    calls[0]+=1
    if calls[0] == 2: raise OSError('injected interruption')
    return replace(*args)
with patch.object(m.os, 'replace', side_effect=fail_after_one):
    m.update(sys.argv[2],sys.argv[3],sys.argv[4],sys.argv[5],sys.argv[6], 'cat/pkg',['misc/owner.txt'])
"""
        result = run([sys.executable, '-B', '-c', code,
                      self.ports / 'scripts/pkgsrc-shared-update.py', self.export,
                      self.ports, GIT, SDK, PATCH], self.ports, check=False)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('injected interruption', result.stderr)
        self.assertTrue(self.marker.exists())
        self.assertEqual(self.receipt.read_bytes(), self.old_receipt)
        self.assertEqual((self.tree / 'misc/owner.txt').read_text(), 'new-owner\n')
        self.assertNotEqual(self.update().returncode, 0)
        write(self.ports, 'unrelated-note.txt', 'same export inputs\n')
        commit(self.ports, 'unrelated commit')
        resumed = self.update('--resume')
        self.assertEqual(resumed.returncode, 0, resumed.stdout + resumed.stderr)
        self.assertFalse(self.marker.exists())
        self.assertEqual((self.tree / 'cat/pkg/Makefile').read_text(), 'PKGNAME=fixture-2\n')
        self.assertFalse((self.tree / 'cat/pkg/files/deleted').exists())

    def test_updated_receipt_is_accepted_by_shared_reader(self):
        self.newer_inputs()
        result = self.update()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        code = ('import importlib.util,sys; s=importlib.util.spec_from_file_location("i",sys.argv[1]); '
                'm=importlib.util.module_from_spec(s);s.loader.exec_module(m); '
                'm.shared_export(sys.argv[2],sys.argv[3],sys.argv[4],sys.argv[5],sys.argv[6])')
        result = run([sys.executable, '-B', '-c', code,
                      self.ports / 'scripts/pkgsrc-source-identity.py', self.export,
                      self.ports, GIT, SDK, PATCH], self.ports, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_uncommitted_new_patch_and_changed_inputs(self):
        self.newer_inputs()
        run([GIT, 'reset', '--mixed', 'HEAD^'], self.ports)
        result = self.update()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.tree / 'cat/pkg/Makefile').read_text(), 'PKGNAME=fixture-2\n')

    def test_two_dirty_updates_and_commit_reuse_active_input_cache(self):
        self.newer_inputs()
        run([GIT, 'reset', '--mixed', 'HEAD^'], self.ports)
        first = self.update()
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        patch = self.ports / 'patches/fixture.patch'
        patch.write_text(patch.read_text().replace('fixture-2', 'fixture-3'))
        write(self.ports, 'resources/owner.txt', 'second-owner\n')
        second = self.update()
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertEqual((self.tree / 'cat/pkg/Makefile').read_text(), 'PKGNAME=fixture-3\n')
        self.assertEqual((self.tree / 'misc/owner.txt').read_text(), 'second-owner\n')
        selected = self.tree / 'cat/pkg/Makefile'
        stamp = (selected.stat().st_ino, selected.stat().st_mtime_ns)
        commit(self.ports, 'commit same inputs')
        third = self.update()
        self.assertEqual(third.returncode, 0, third.stdout + third.stderr)
        self.assertEqual((selected.stat().st_ino, selected.stat().st_mtime_ns), stamp)
        cache = self.export / '.pkgsrc-update-inputs'
        self.assertFalse(cache.exists() and any(cache.iterdir()))

    def test_dirty_package_a_then_dirty_package_b(self):
        self.newer_inputs()
        run([GIT, 'reset', '--mixed', 'HEAD^'], self.ports)
        first = self.update()
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        patch = ('--- a/cat/other/Makefile\n+++ b/cat/other/Makefile\n'
                 '@@ -1 +1 @@\n-PKGNAME=other-1\n+PKGNAME=other-2\n')
        write(self.ports, 'patches/other.patch', patch)
        conf = self.ports / 'pkgsrc/export.conf'
        conf.write_text(conf.read_text() + 'patch\tpatches/other.patch\n')
        result = run(self.command + ['--update', '--package', 'cat/other'], self.ports, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.tree / 'cat/pkg/Makefile').read_text(), 'PKGNAME=fixture-2\n')
        self.assertEqual((self.tree / 'cat/other/Makefile').read_text(), 'PKGNAME=other-2\n')

    def test_corrupt_dirty_cache_is_refused_before_writes(self):
        self.newer_inputs()
        run([GIT, 'reset', '--mixed', 'HEAD^'], self.ports)
        first = self.update()
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        receipt = json.loads(self.receipt.read_text())
        sha = receipt['dirty_inputs']['patches/fixture.patch']['sha256']
        blob = self.export / '.pkgsrc-update-inputs' / sha
        original = blob.read_bytes()
        patch = self.ports / 'patches/fixture.patch'
        patch.write_text(patch.read_text().replace('fixture-2', 'fixture-3'))
        before = self.receipt.read_bytes()
        for corruption in ('content', 'mode'):
            with self.subTest(corruption=corruption):
                if corruption == 'content':
                    blob.write_bytes(b'wrong')
                else:
                    blob.chmod(0o644)
                result = self.update()
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(self.receipt.read_bytes(), before)
                self.assertFalse(self.marker.exists())
                blob.write_bytes(original)
                blob.chmod(0o600)

    def test_malformed_previous_digest_is_refused_before_cache_lookup(self):
        self.newer_inputs()
        run([GIT, 'reset', '--mixed', 'HEAD^'], self.ports)
        first = self.update()
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        record = json.loads(self.receipt.read_text())
        record['inputs']['files']['pkgsrc/export.conf'] = '../../outside'
        encoded = json.dumps(record['inputs'], sort_keys=True, separators=(',', ':')).encode()
        record['identity']['export_inputs_sha256'] = hashlib.sha256(encoded).hexdigest()
        self.receipt.write_text(json.dumps(record, sort_keys=True) + '\n')
        result = self.update()
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('invalid previous input digest', result.stderr)
        self.assertFalse(self.marker.exists())

    def test_selected_file_mode_change_without_content_change(self):
        (self.ports / 'resources/owner.txt').chmod(0o755)
        commit(self.ports, 'change file mode')
        result = self.update()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.tree / 'misc/owner.txt').stat().st_mode & 0o777, 0o755)
        self.assertEqual((self.tree / 'misc/owner.txt').read_text(), 'old-owner\n')

    def test_refuses_modified_live_input(self):
        self.newer_inputs()
        # A changed live output must never be mistaken for the old baseline.
        (self.tree / 'cat/pkg/files/unchanged').write_text('local edit\n')
        result = self.update()
        self.assert_refused_unchanged(result)
        self.assertEqual((self.tree / 'cat/pkg/files/unchanged').read_text(), 'local edit\n')

    def test_refuses_unselected_global_change(self):
        self.newer_inputs()
        write(self.ports, 'pkgsrc/versions.mk', 'EMBERBSD_VERSION_FAMILIES+= bad=bad\n')
        result = self.update()
        self.assert_refused_unchanged(result)

    def test_existing_interruption_marker_blocks_update_and_reader(self):
        self.newer_inputs()
        self.marker.write_text('interrupted\n')
        self.assert_refused_unchanged(self.update())
        self.assertTrue(self.marker.exists())
        check = run([sys.executable, '-B', '-c',
                     'import importlib.util,sys; s=importlib.util.spec_from_file_location("i",sys.argv[1]); '
                     'm=importlib.util.module_from_spec(s);s.loader.exec_module(m); '
                     'm.shared_export(sys.argv[2],sys.argv[3],sys.argv[4],sys.argv[5],sys.argv[6])',
                     self.ports / 'scripts/pkgsrc-source-identity.py', self.export, self.ports,
                     GIT, SDK, PATCH], self.ports, check=False)
        self.assertNotEqual(check.returncode, 0)
        self.assertIn('update is incomplete', check.stderr)

    def test_rejects_escaping_selected_file(self):
        self.newer_inputs()
        self.assert_refused_unchanged(self.update('--file', '../escape'))


if __name__ == '__main__':
    unittest.main()
