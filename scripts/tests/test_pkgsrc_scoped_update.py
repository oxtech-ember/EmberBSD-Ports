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
        write(upstream, 'mk/bsd.makevars.mk', 'makevars=0\n')
        write(upstream, 'mk/buildlink3/bsd.buildlink3.mk', 'buildlink=0\n')
        write(upstream, 'mk/neighbor.mk', 'neighbor=0\n')
        run([GIT, 'add', '-f', 'mk/bsd.makevars.mk', 'mk/buildlink3/bsd.buildlink3.mk', 'mk/neighbor.mk'], upstream)
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

    def new_overlay(self):
        write(self.ports, 'pkgsrc/cat/new/Makefile', 'PKGNAME=new-1\n')
        write(self.ports, 'pkgsrc/cat/new/files/data', 'new data\n')
        commit(self.ports, 'new package')

    def test_new_non_upstream_overlay_preserves_neighbor(self):
        self.new_overlay()
        neighbor = self.tree / 'cat/pkg/Makefile'
        stamp = (neighbor.stat().st_ino, neighbor.stat().st_mtime_ns)
        result = run(self.command + ['--update', '--package', 'cat/new'], self.ports, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.tree / 'cat/new/files/data').read_text(), 'new data\n')
        self.assertEqual((neighbor.stat().st_ino, neighbor.stat().st_mtime_ns), stamp)

    def test_new_overlay_refuses_existing_empty_or_symlink_path(self):
        self.new_overlay()
        for symlink in (False, True):
            target = self.tree / 'cat/new'
            if symlink:
                target.symlink_to(self.tree / 'cat/pkg', target_is_directory=True)
            else:
                target.mkdir()
            result = run(self.command + ['--update', '--package', 'cat/new'], self.ports, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(self.marker.exists())
            self.assertEqual(self.receipt.read_bytes(), self.old_receipt)
            target.unlink() if symlink else target.rmdir()

    def test_interrupted_new_overlay_resumes(self):
        self.new_overlay()
        code = r'''import importlib.util,sys
from unittest.mock import patch
s=importlib.util.spec_from_file_location('u',sys.argv[1]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
replace=m.os.replace
calls=[0]
def fail_after_one(*args):
    calls[0]+=1
    if calls[0] == 2: raise OSError('injected addition interruption')
    return replace(*args)
with patch.object(m.os, 'replace', side_effect=fail_after_one):
    m.update(sys.argv[2],sys.argv[3],sys.argv[4],sys.argv[5],sys.argv[6], 'cat/new', [])
'''
        result = run([sys.executable, '-B', '-c', code, self.ports / 'scripts/pkgsrc-shared-update.py',
                      self.export, self.ports, GIT, SDK, PATCH], self.ports, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(self.marker.exists())
        result = run(self.command + ['--update', '--package', 'cat/new', '--resume'], self.ports, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.tree / 'cat/new/files/data').read_text(), 'new data\n')
        self.assertFalse(self.marker.exists())

    def test_global_patch_chain_and_resume(self):
        names = ('mk/bsd.makevars.mk', 'mk/buildlink3/bsd.buildlink3.mk')
        def patch(old, new):
            return ''.join(f'--- a/{name}\n+++ b/{name}\n@@ -1 +1 @@\n-{key}={old}\n+{key}={new}\n'
                           for name, key in zip(names, ('makevars', 'buildlink')))
        write(self.ports, 'patches/one.patch', patch(0, 1))
        write(self.ports, 'patches/two.patch', patch(1, 2))
        conf = self.ports / 'pkgsrc/export.conf'
        conf.write_text(conf.read_text() + 'patch\tpatches/one.patch\npatch\tpatches/two.patch\n')
        commit(self.ports, 'global patch chain')
        args = ['--file', names[0], '--file', names[1]]
        neighbor = self.tree / 'mk/neighbor.mk'
        stamp = (neighbor.stat().st_ino, neighbor.stat().st_mtime_ns)
        rejected = self.update('--file', names[0])
        self.assertNotEqual(rejected.returncode, 0)
        self.assertEqual((self.tree / names[0]).read_text(), 'makevars=0\n')
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
    m.update(sys.argv[2],sys.argv[3],sys.argv[4],sys.argv[5],sys.argv[6], ['cat/pkg'], ['misc/owner.txt', 'mk/bsd.makevars.mk', 'mk/buildlink3/bsd.buildlink3.mk'])
"""
        result = run([sys.executable, '-B', '-c', code, self.ports / 'scripts/pkgsrc-shared-update.py',
                      self.export, self.ports, GIT, SDK, PATCH], self.ports, check=False)
        self.assertIn('injected interruption', result.stderr)
        self.assertTrue(self.marker.exists())
        result = self.update(*args, '--resume')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.tree / names[0]).read_text(), 'makevars=2\n')
        self.assertEqual((self.tree / names[1]).read_text(), 'buildlink=2\n')
        self.assertEqual((neighbor.stat().st_ino, neighbor.stat().st_mtime_ns), stamp)
        self.assertFalse(self.marker.exists())
        write(self.ports, 'patches/two.patch', patch(1, 3))
        commit(self.ports, 'change second global patch')
        selected = self.tree / names[0]
        selected.write_text('local drift\n')
        refused = self.update(*args)
        self.assertNotEqual(refused.returncode, 0)
        self.assertEqual(selected.read_text(), 'local drift\n')
        selected.write_text('makevars=2\n')
        result = self.update(*args)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(selected.read_text(), 'makevars=3\n')
        self.assertEqual((self.tree / names[1]).read_text(), 'buildlink=3\n')
        self.assertEqual((neighbor.stat().st_ino, neighbor.stat().st_mtime_ns), stamp)

    def test_global_patch_orig_header(self):
        name = 'mk/bsd.makevars.mk'
        def patch(old_name, new_name, old, new):
            return (f'--- a/{old_name}\n+++ b/{new_name}\n@@ -1 +1 @@\n'
                    f'-makevars={old}\n+makevars={new}\n')
        write(self.ports, 'patches/orig.patch', patch(name + '.orig', name, 0, 1))
        conf = self.ports / 'pkgsrc/export.conf'
        conf.write_text(conf.read_text() + 'patch\tpatches/orig.patch\n')
        commit(self.ports, 'existing orig header')
        self.export = self.work / 'orig-shared'
        self.command[3] = self.export
        result = run(self.command, self.ports, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.tree = self.export / 'pkgsrc'
        self.assertEqual((self.tree / name).read_text(), 'makevars=1\n')
        write(self.ports, 'patches/next.patch', patch(name, name, 1, 2))
        conf.write_text(conf.read_text() + 'patch\tpatches/next.patch\n')
        commit(self.ports, 'next global patch')
        result = self.update('--file', name)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.tree / name).read_text(), 'makevars=2\n')
        for old, new in [('mk/other.mk', name), (name, name + '.orig')]:
            write(self.ports, 'patches/next.patch', patch(old, new, 1, 2))
            result = self.update('--file', name)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('changed patch extends outside selected package', result.stderr)
            self.assertEqual((self.tree / name).read_text(), 'makevars=2\n')
        self.assertEqual((self.tree / 'mk/neighbor.mk').read_text(), 'neighbor=0\n')

    def test_global_patch_created_file_update_and_foreign_preimage(self):
        name = 'mk/tools/ember-created.mk'
        def creation(value):
            return (f'--- a/{name}\n+++ b/{name}\n@@ -0,0 +1 @@\n+value={value}\n')
        patch = self.ports / 'patches/create.patch'
        write(self.ports, 'patches/create.patch', creation('old'))
        conf = self.ports / 'pkgsrc/export.conf'
        conf.write_text(conf.read_text() + 'patch\tpatches/create.patch\n')
        commit(self.ports, 'create global file')
        self.export = self.work / 'created-shared'; self.command[3] = self.export
        initial = run(self.command, self.ports, check=False)
        self.assertEqual(initial.returncode, 0, initial.stdout + initial.stderr)
        self.tree = self.export / 'pkgsrc'; self.receipt = self.export / 'pkgsrc-export.json'
        self.marker = self.export / '.pkgsrc-update-incomplete'
        self.old_receipt = self.receipt.read_bytes()
        selected = self.tree / name; neighbor = self.tree / 'mk/neighbor.mk'
        self.assertEqual(selected.read_text(), 'value=old\n')
        stamp = (neighbor.stat().st_ino, neighbor.stat().st_mtime_ns)
        patch.write_text(creation('new')); commit(self.ports, 'change created global file')
        selected.write_text('foreign\n')
        result = self.update('--file', name)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(selected.read_text(), 'foreign\n')
        self.assertEqual(self.receipt.read_bytes(), self.old_receipt)
        self.assertFalse(self.marker.exists())
        selected.write_text('value=old\n')
        result = self.update('--file', name)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(selected.read_text(), 'value=new\n')
        self.assertEqual((neighbor.stat().st_ino, neighbor.stat().st_mtime_ns), stamp)

    def test_global_patch_missing_creator_is_refused_before_write(self):
        name = 'mk/tools/ember-created.mk'
        patch = self.ports / 'patches/create.patch'
        write(self.ports, 'patches/create.patch',
              f'--- a/{name}\n+++ b/{name}\n@@ -0,0 +1 @@\n+value=old\n')
        conf = self.ports / 'pkgsrc/export.conf'
        conf.write_text(conf.read_text() + 'patch\tpatches/create.patch\n')
        commit(self.ports, 'create global file')
        self.export = self.work / 'missing-creator'; self.command[3] = self.export
        initial = run(self.command, self.ports, check=False)
        self.assertEqual(initial.returncode, 0, initial.stdout + initial.stderr)
        self.tree = self.export / 'pkgsrc'; self.receipt = self.export / 'pkgsrc-export.json'
        self.marker = self.export / '.pkgsrc-update-incomplete'
        before = self.receipt.read_bytes(); selected = self.tree / name
        neighbor = self.tree / 'mk/neighbor.mk'; stamp = (neighbor.stat().st_ino, neighbor.stat().st_mtime_ns)
        patch.write_text(f'--- a/{name}\n+++ b/{name}\n@@ -1 +1 @@\n-value=old\n+value=new\n')
        commit(self.ports, 'remove creator')
        result = self.update('--file', name)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(selected.read_text(), 'value=old\n')
        self.assertEqual(self.receipt.read_bytes(), before)
        self.assertFalse(self.marker.exists())
        self.assertEqual((neighbor.stat().st_ino, neighbor.stat().st_mtime_ns), stamp)

    def test_global_patch_dev_null_creator(self):
        name = 'mk/tools/ember-null-created.mk'
        def creation(value):
            return f'--- /dev/null\n+++ b/{name}\n@@ -0,0 +1 @@\n+value={value}\n'
        patch = self.ports / 'patches/null-create.patch'
        write(self.ports, 'patches/null-create.patch', creation('old'))
        conf = self.ports / 'pkgsrc/export.conf'
        conf.write_text(conf.read_text() + 'patch\tpatches/null-create.patch\n')
        commit(self.ports, 'create global file from dev null')
        self.export = self.work / 'null-created'; self.command[3] = self.export
        initial = run(self.command, self.ports, check=False)
        self.assertEqual(initial.returncode, 0, initial.stdout + initial.stderr)
        self.tree = self.export / 'pkgsrc'
        patch.write_text(creation('new')); commit(self.ports, 'change null-created global file')
        result = self.update('--file', name)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.tree / name).read_text(), 'value=new\n')

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

    def test_existing_multifile_git_patch_is_replayed_only_for_selected_package(self):
        patch = ('# Existing shared recipe patch.\n'
                 'diff --git a/cat/pkg/Makefile b/cat/pkg/Makefile\n'
                 'index 1234567..abcdef0 100644\n'
                 '--- a/cat/pkg/Makefile\n+++ b/cat/pkg/Makefile\n'
                 '@@ -1 +1 @@\n-PKGNAME=fixture-1\n+PKGNAME=fixture-2\n'
                 'diff --git a/cat/other/Makefile b/cat/other/Makefile\n'
                 'index 7654321..fedcba0 100644\n'
                 '--- a/cat/other/Makefile\n+++ b/cat/other/Makefile\n'
                 '@@ -1 +1 @@\n-PKGNAME=other-1\n+PKGNAME=other-2\n')
        write(self.ports, 'patches/shared.patch', patch)
        config = ('patch\tpatches/shared.patch\n'
                  'file\tresources/owner.txt\tmisc/owner.txt\n')
        write(self.ports, 'pkgsrc/export.conf', config)
        commit(self.ports, 'existing git-formatted shared patch')
        self.export = self.work / 'shared-git'
        self.command[3] = self.export
        run(self.command, self.ports)
        self.tree = self.export / 'pkgsrc'
        self.receipt = self.export / 'pkgsrc-export.json'
        self.marker = self.export / '.pkgsrc-update-incomplete'
        other = self.tree / 'cat/other/Makefile'
        before = (other.stat().st_ino, other.stat().st_mtime_ns)
        write(self.ports, 'patches/next.patch',
              '--- a/cat/pkg/Makefile\n+++ b/cat/pkg/Makefile\n'
              '@@ -1 +1 @@\n-PKGNAME=fixture-2\n+PKGNAME=fixture-3\n')
        write(self.ports, 'pkgsrc/export.conf', config + 'patch\tpatches/next.patch\n')
        commit(self.ports, 'change only selected package')
        result = self.update()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.tree / 'cat/pkg/Makefile').read_text(), 'PKGNAME=fixture-3\n')
        self.assertEqual(other.read_text(), 'PKGNAME=other-2\n')
        self.assertEqual((other.stat().st_ino, other.stat().st_mtime_ns), before)
        self.assertFalse(self.marker.exists())

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

    def test_multi_package_shared_patch_atomic_resume(self):
        write(self.ports, 'pkgsrc/replaces', 'cat/pkg\n')
        write(self.ports, 'pkgsrc/cat/pkg/Makefile', 'PKGNAME=fixture-1\n')
        write(self.ports, 'pkgsrc/cat/pkg/files/unchanged', 'retained\n')
        write(self.ports, 'pkgsrc/cat/pkg/files/modified', 'old\n')
        def shared_patch(value):
            return ('--- a/cat/pkg/Makefile\n+++ b/cat/pkg/Makefile\n'
                    '@@ -1 +1 @@\n-PKGNAME=fixture-1\n+PKGNAME=fixture-' + value + '\n'
                    '--- a/cat/other/Makefile\n+++ b/cat/other/Makefile\n'
                    '@@ -1 +1 @@\n-PKGNAME=other-1\n+PKGNAME=other-' + value + '\n')
        write(self.ports, 'patches/shared.patch', shared_patch('2'))
        conf = self.ports / 'pkgsrc/export.conf'
        conf.write_text(conf.read_text() + 'patch\tpatches/shared.patch\n')
        commit(self.ports, 'overlay and shared patch')
        self.export = self.work / 'multi'
        self.command[3] = self.export
        result = run(self.command, self.ports, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.tree = self.export / 'pkgsrc'
        self.receipt = self.export / 'pkgsrc-export.json'
        self.marker = self.export / '.pkgsrc-update-incomplete'
        before = self.receipt.read_bytes()
        retained = self.tree / 'cat/pkg/files/unchanged'
        stamp = (retained.stat().st_ino, retained.stat().st_mtime_ns)
        write(self.ports, 'pkgsrc/cat/pkg/files/modified', 'new\n')
        write(self.ports, 'patches/shared.patch', shared_patch('3'))
        commit(self.ports, 'update both scopes')
        one = run(self.command + ['--update', '--package', 'cat/pkg'], self.ports, check=False)
        self.assertNotEqual(one.returncode, 0)
        self.assertEqual(self.receipt.read_bytes(), before)
        code = r"""import importlib.util,sys
from unittest.mock import patch
s=importlib.util.spec_from_file_location('u',sys.argv[1]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
replace=m.os.replace
calls=[0]
def fail_after_one(*args):
    calls[0]+=1
    if calls[0] == 2: raise OSError('multi interruption')
    return replace(*args)
with patch.object(m.os, 'replace', side_effect=fail_after_one):
    m.update(sys.argv[2],sys.argv[3],sys.argv[4],sys.argv[5],sys.argv[6], ['cat/pkg','cat/other'],[])
"""
        result = run([sys.executable, '-B', '-c', code, self.ports / 'scripts/pkgsrc-shared-update.py',
                      self.export, self.ports, GIT, SDK, PATCH], self.ports, check=False)
        self.assertIn('multi interruption', result.stderr)
        self.assertTrue(self.marker.exists())
        self.assertEqual(self.receipt.read_bytes(), before)
        write(self.ports, 'pkgsrc/cat/pkg/files/modified', 'changed during interruption\n')
        resume = self.command + ['--update', '--package', 'cat/pkg', '--package', 'cat/other', '--resume']
        self.assertNotEqual(run(resume, self.ports, check=False).returncode, 0)
        write(self.ports, 'pkgsrc/cat/pkg/files/modified', 'new\n')
        result = run(resume, self.ports, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(self.marker.exists())
        self.assertEqual((self.tree / 'cat/pkg/Makefile').read_text(), 'PKGNAME=fixture-3\n')
        self.assertEqual((self.tree / 'cat/other/Makefile').read_text(), 'PKGNAME=other-3\n')
        self.assertEqual((self.tree / 'cat/pkg/files/modified').read_text(), 'new\n')
        self.assertEqual((retained.stat().st_ino, retained.stat().st_mtime_ns), stamp)

    def test_existing_overlay_recipe_supports_repeated_dirty_updates(self):
        recipe = self.ports / 'pkgsrc/cat/pkg'
        write(self.ports, 'pkgsrc/replaces', 'cat/pkg\n')
        write(self.ports, 'pkgsrc/cat/pkg/Makefile', 'PKGNAME=overlay-1\n')
        old_patch = b'old patch payload\n'
        kept_patch = b'kept patch payload\n'
        (recipe / 'patches').mkdir()
        (recipe / 'patches/patch-old').write_bytes(old_patch)
        (recipe / 'patches/patch-kept').write_bytes(kept_patch)
        old_line = 'SHA1 (patch-old) = ' + hashlib.sha1(old_patch).hexdigest() + '\n'
        kept_line = 'SHA1 (patch-kept) = ' + hashlib.sha1(kept_patch).hexdigest() + '\n'
        (recipe / 'distinfo').write_text(old_line + kept_line)
        write(self.ports, 'pkgsrc/cat/pkg/files/unchanged', 'overlay-unchanged\n')
        write(self.ports, 'resources/extra-patch', 'extra patch payload\n')
        write(self.ports, 'resources/extra-file', 'old extra file\n')
        conf = self.ports / 'pkgsrc/export.conf'
        conf.write_text(conf.read_text() + 'recipe-patch\tresources/extra-patch\tcat/pkg\tpatch-extra\n' +
                        'file\tresources/extra-file\tcat/pkg/files/extra\n' +
                        'file\tresources/extra-patch\tmisc/shared-patch\n')
        commit(self.ports, 'existing overlay')
        self.export = self.work / 'overlay-shared'
        self.command[3] = self.export
        result = run(self.command, self.ports, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.tree = self.export / 'pkgsrc'
        self.receipt = self.export / 'pkgsrc-export.json'
        unchanged = self.tree / 'cat/pkg/files/unchanged'
        before = (unchanged.stat().st_ino, unchanged.stat().st_mtime_ns)
        (recipe / 'Makefile').write_text('PKGNAME=overlay-2\n')
        (recipe / 'patches/patch-old').unlink()
        (recipe / 'distinfo').write_text(kept_line)
        write(self.ports, 'resources/extra-file', 'new extra file\n')
        first = self.update()
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertEqual((self.tree / 'cat/pkg/Makefile').read_text(), 'PKGNAME=overlay-2\n')
        self.assertFalse((self.tree / 'cat/pkg/patches/patch-old').exists())
        self.assertEqual((self.tree / 'cat/pkg/patches/patch-extra').read_text(), 'extra patch payload\n')
        self.assertEqual((self.tree / 'cat/pkg/files/extra').read_text(), 'new extra file\n')
        self.assertEqual((unchanged.stat().st_ino, unchanged.stat().st_mtime_ns), before)
        (recipe / 'Makefile').write_text('PKGNAME=overlay-3\n')
        (recipe / 'patches/patch-kept').unlink()
        (recipe / 'patches').rmdir()
        (recipe / 'distinfo').write_text('')
        second = self.update()
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertEqual((self.tree / 'cat/pkg/Makefile').read_text(), 'PKGNAME=overlay-3\n')
        self.assertFalse((self.tree / 'cat/pkg/patches/patch-kept').exists())
        self.assertTrue((self.tree / 'cat/pkg/patches/patch-extra').is_file())
        self.assertEqual((unchanged.stat().st_ino, unchanged.stat().st_mtime_ns), before)
        receipt = self.receipt.read_bytes()
        write(self.ports, 'resources/extra-patch', 'changed shared patch\n')
        rejected = self.update()
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn('recipe patch source has other export consumers', rejected.stderr)
        self.assertEqual(self.receipt.read_bytes(), receipt)
        self.assertEqual((self.tree / 'misc/shared-patch').read_text(), 'extra patch payload\n')

    def test_overlay_symlink_consumers_and_dirty_reuse(self):
        write(self.ports, 'pkgsrc/replaces', 'cat/pkg\ncat/other\n')
        for name in ('pkg', 'other', 'shared'):
            write(self.ports, 'pkgsrc/cat/' + name + '/Makefile', 'PKGNAME=' + name + '-1\n')
        target = write(self.ports, 'pkgsrc/cat/shared/files/producer', 'old\n')
        write(self.ports, 'pkgsrc/cat/shared/files/alternate', 'alternate\n')
        (target.parent / 'alias').symlink_to('producer')
        for name in ('pkg', 'other'):
            files = self.ports / 'pkgsrc/cat' / name / 'files'
            files.mkdir()
            (files / 'producer').symlink_to('../../shared/files/alias')
            write(self.ports, 'pkgsrc/cat/' + name + '/files/unchanged', 'retained\n')
        commit(self.ports, 'overlay links')
        self.export = self.work / 'links'
        self.command[3] = self.export
        result = run(self.command, self.ports, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.tree = self.export / 'pkgsrc'
        self.receipt = self.export / 'pkgsrc-export.json'
        a = self.tree / 'cat/pkg/files/producer'
        b = self.tree / 'cat/other/files/producer'
        retained = self.tree / 'cat/pkg/files/unchanged'
        stamp = (retained.stat().st_ino, retained.stat().st_mtime_ns)
        self.assertEqual(a.read_text(), 'old\n')
        self.assertEqual(b.read_text(), 'old\n')
        target.write_text('new\n')
        before = self.receipt.read_bytes()
        one = run(self.command + ['--update', '--package', 'cat/pkg', '--package', 'cat/shared'],
                  self.ports, check=False)
        self.assertNotEqual(one.returncode, 0, one.stdout + one.stderr)
        self.assertEqual(self.receipt.read_bytes(), before)
        self.assertEqual(a.read_text(), 'old\n')
        args = ['--update', '--package', 'cat/pkg', '--package', 'cat/other',
                '--package', 'cat/shared']
        result = run(self.command + args, self.ports, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(a.read_text(), 'new\n')
        self.assertEqual(b.read_text(), 'new\n')
        self.assertEqual((retained.stat().st_ino, retained.stat().st_mtime_ns), stamp)
        target.write_text('newer\n')
        result = run(self.command + args, self.ports, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(a.read_text(), 'newer\n')
        self.assertEqual(b.read_text(), 'newer\n')
        unchanged = (a.stat().st_ino, a.stat().st_mtime_ns)
        commit(self.ports, 'commit dirty producer')
        result = run(self.command + args, self.ports, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((a.stat().st_ino, a.stat().st_mtime_ns), unchanged)
        # A mode-only target change affects every materialized consumer.
        target.chmod(0o755)
        before = self.receipt.read_bytes()
        one = run(self.command + ['--update', '--package', 'cat/shared'], self.ports, check=False)
        self.assertNotEqual(one.returncode, 0, one.stdout + one.stderr)
        self.assertEqual(self.receipt.read_bytes(), before)
        result = run(self.command + args, self.ports, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(a.stat().st_mode & 0o777, 0o755)
        self.assertEqual(b.stat().st_mode & 0o777, 0o755)
        commit(self.ports, "commit executable producer")
        target.chmod(0o644)
        result = run(self.command + args, self.ports, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(a.stat().st_mode & 0o777, 0o644)
        commit(self.ports, 'commit restored mode')
        unchanged = (a.stat().st_ino, a.stat().st_mtime_ns)
        result = run(self.command + args, self.ports, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((a.stat().st_ino, a.stat().st_mtime_ns), unchanged)
        alias = target.parent / 'alias'
        alias.unlink()
        alias.symlink_to('alternate')
        commit(self.ports, 'change alias target')
        result = run(self.command + args, self.ports, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(a.read_text(), 'alternate\n')
        self.assertEqual(b.read_text(), 'alternate\n')
        self.assertEqual((retained.stat().st_ino, retained.stat().st_mtime_ns), stamp)
        # Removing one materialized source link removes its exported file.
        (self.ports / 'pkgsrc/cat/pkg/files/producer').unlink()
        commit(self.ports, 'remove consumer link')
        result = run(self.command + args, self.ports, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(a.exists())
        self.assertEqual(b.read_text(), 'alternate\n')

    def test_v2_link_deletion_and_dirty_retarget(self):
        write(self.ports, 'pkgsrc/replaces', 'cat/pkg\n')
        write(self.ports, 'pkgsrc/cat/pkg/Makefile', 'PKGNAME=pkg-1\n')
        files = self.ports / 'pkgsrc/cat/pkg/files'
        files.mkdir()
        write(self.ports, 'pkgsrc/cat/pkg/files/first', 'first\n')
        write(self.ports, 'pkgsrc/cat/pkg/files/second', 'second\n')
        link = files / 'link'
        link.symlink_to('first')
        commit(self.ports, 'initial link')
        self.export = self.work / 'v2-link'
        self.command[3] = self.export
        result = run(self.command, self.ports, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.receipt = self.export / 'pkgsrc-export.json'
        self.assertEqual(json.loads(self.receipt.read_text())['version'], 2)
        self.tree = self.export / 'pkgsrc'
        output = self.tree / 'cat/pkg/files/link'
        link.unlink()
        commit(self.ports, 'delete link')
        args = ['--update', '--package', 'cat/pkg']
        result = run(self.command + args, self.ports, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(output.exists())
        link.symlink_to('first')
        result = run(self.command + args, self.ports, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(output.read_text(), 'first\n')
        link.unlink()
        link.symlink_to('second')
        result = run(self.command + args, self.ports, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(output.read_text(), 'second\n')
        link.unlink()
        link.symlink_to('first')
        result = run(self.command + args, self.ports, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(output.read_text(), 'first\n')
        stamp = (output.stat().st_ino, output.stat().st_mtime_ns)
        commit(self.ports, 'commit retarget')
        result = run(self.command + args, self.ports, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((output.stat().st_ino, output.stat().st_mtime_ns), stamp)

    def _upstream_recipe_becomes_selected_overlay(self, version):
        with self.subTest(version=version):
            if version == 3:
                result = self.update()
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            old = self.receipt.read_bytes()
            retained = self.tree / 'cat/other/Makefile'
            stamp = (retained.stat().st_ino, retained.stat().st_mtime_ns)
            write(self.ports, 'pkgsrc/replaces', 'cat/pkg\ncat/other\n')
            write(self.ports, 'pkgsrc/cat/pkg/Makefile', 'PKGNAME=overlay-1\n')
            refused = run(self.command + ['--update', '--package', 'cat/pkg'], self.ports, check=False)
            self.assertNotEqual(refused.returncode, 0)
            self.assertEqual(self.receipt.read_bytes(), old)
            write(self.ports, 'pkgsrc/replaces', 'cat/pkg\n')
            result = run(self.command + ['--update', '--package', 'cat/pkg'], self.ports, check=False)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual((self.tree / 'cat/pkg/Makefile').read_text(), 'PKGNAME=overlay-1\n')
            self.assertEqual((retained.stat().st_ino, retained.stat().st_mtime_ns), stamp)
            selected = self.tree / 'cat/pkg/Makefile'
            selected_stamp = (selected.stat().st_ino, selected.stat().st_mtime_ns)
            commit(self.ports, 'commit overlay')
            result = run(self.command + ['--update', '--package', 'cat/pkg'], self.ports, check=False)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual((selected.stat().st_ino, selected.stat().st_mtime_ns), selected_stamp)
            write(self.ports, 'pkgsrc/cat/pkg/Makefile', 'PKGNAME=overlay-2\n')
            result = run(self.command + ['--update', '--package', 'cat/pkg'], self.ports, check=False)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(selected.read_text(), 'PKGNAME=overlay-2\n')

    def test_upstream_recipe_becomes_selected_overlay_v2(self):
        self._upstream_recipe_becomes_selected_overlay(2)

    def test_upstream_recipe_becomes_selected_overlay_v3(self):
        self._upstream_recipe_becomes_selected_overlay(3)

    def test_shared_file_source_requires_all_consumers(self):
        conf = self.ports / 'pkgsrc/export.conf'
        conf.write_text(conf.read_text() + 'file\tresources/owner.txt\tcat/pkg/files/other-owner\n')
        commit(self.ports, 'shared file source')
        self.export = self.work / 'shared-source'
        self.command[3] = self.export
        result = run(self.command, self.ports, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.tree = self.export / 'pkgsrc'
        self.receipt = self.export / 'pkgsrc-export.json'
        before = self.receipt.read_bytes()
        write(self.ports, 'resources/owner.txt', 'changed\n')
        result = run(self.command + ['--update', '--package', 'cat/pkg'], self.ports, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('another export consumer', result.stderr)
        self.assertEqual(self.receipt.read_bytes(), before)
        self.assertEqual((self.tree / 'misc/owner.txt').read_text(), 'old-owner\n')

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
