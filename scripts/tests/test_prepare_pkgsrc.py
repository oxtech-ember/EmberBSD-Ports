#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD; AI-assisted finite exporter regressions.
"""Test export semantics with explicit host regression tools, never seed admission."""

import hashlib
import importlib.util
import io
import os
from pathlib import Path
import stat
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('fixture', HERE / 'export-fixture.py')
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
exporter = fixture.load_exporter(HERE.parents[1])

# Use the actual SDK error class. The source is explicit; these tests do not
# run SDK producers or qualify a toolset.
sdk_root = os.environ.get('EMBERBSD_SDK_SOURCE')
if not sdk_root:
    raise ValueError('Set EMBERBSD_SDK_SOURCE for the SDK ownership-error control.')
helper_path = HERE.parents[1] / 'profiles/development-toolchain/runtime/recipe/files/sdk_source.py'
spec = importlib.util.spec_from_file_location('source_test_sdk', helper_path)
sdk_source = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sdk_source)
sdk_source.load(sdk_root)
from emberbsd_sdk.errors import ProcessOwnershipError


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='pkgsrc-source-test.')
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)
        self.root = self.work / 'ports'
        (self.root / 'pkgsrc').mkdir(parents=True)
        (self.root / 'pkgsrc/export.conf').write_bytes(b'')
        self.upstream = self.work / 'upstream'
        self.upstream.mkdir()
        (self.upstream / 'plain').write_bytes(b'one\ntwo\nthree\n')
        self.selected = fixture.TestSelection()
        self.commands = []

    def runner(self, argv, **kwargs):
        self.commands.append((argv, kwargs))
        return fixture.test_runner(argv, **kwargs)

    def fake_export(self, name='export', runner=None):
        with mock.patch.dict(os.environ, FAKE_ARCHIVE=str(self.upstream), FAKE_MATCH='1'):
            scratch = self.work / (name + '-scratch')
            result = exporter.export_pkgsrc(self.root, self.work / name,
                selection=self.selected, runner=runner or self.runner, scratch=scratch)
            shutil.rmtree(scratch)  # The test runner has returned with proven test completion.
            return result

    def test_sha1_is_binary_and_filters_whole_lf_records(self):
        path = self.work / 'patch-test'
        path.write_bytes(b'first\r\n$NetBSD: source $\r\n\xff\rbare\nlast')
        self.assertEqual(exporter.patch_sha1(path),
                         hashlib.sha1(b'first\r\n\xff\rbare\nlast').hexdigest())

    def test_intermediate_relative_link_cannot_resolve_outside_repository(self):
        recipe = self.root / 'pkgsrc/devel/link-control'
        recipe.mkdir(parents=True)
        (recipe / 'Makefile').write_text('PKGNAME=link-control-1\n')
        (self.root / 'inside').mkdir()
        (self.root / 'inside/payload').write_bytes(b'inside')
        (self.work / 'payload').write_bytes(b'outside')
        intermediate = self.root / 'bridge'
        intermediate.symlink_to('inside')
        selected = recipe / 'linked-file'
        selected.symlink_to('../../../bridge/payload')
        exporter.check_recipe(recipe, 'pkgsrc/devel/link-control', self.root)
        intermediate.unlink()
        intermediate.symlink_to('..')
        self.assertTrue(Path(os.path.abspath(selected.parent / os.readlink(selected))).is_relative_to(self.root))
        self.assertEqual(selected.read_bytes(), b'outside')
        with self.assertRaisesRegex(exporter.ExportError, 'Link leaves the repository'):
            exporter.check_recipe(recipe, 'pkgsrc/devel/link-control', self.root)

    def test_contained_profile_copies_preserve_missing_patch_refusals(self):
        owner = self.work / 'source-owner'
        cases = [('profiles', 'devel/meson'), ('probes', 'lang/llvm')]
        patch_bytes = b'--- a/value\n+++ b/value\n@@ -1 +1 @@\n-old\n+new\n'
        for tree, recipe in cases:
            (owner / tree).mkdir(parents=True)
            (owner / tree / 'shared.patch').write_bytes(patch_bytes)
            (self.root / tree).symlink_to(owner / tree)
            directory = self.root / 'pkgsrc' / recipe
            (directory / 'patches').mkdir(parents=True)
            (directory / 'Makefile').write_text('PKGNAME=fixture-1\n')
            (directory / 'distinfo').write_text(
                'SHA1 (patch-shared) = ' + hashlib.sha1(patch_bytes).hexdigest() + '\n')
            target = os.path.relpath(self.root / tree / 'shared.patch', directory / 'patches')
            (directory / 'patches/patch-shared').symlink_to(target)
        with self.assertRaisesRegex(exporter.ExportError, 'Link leaves the repository'):
            exporter.configuration(self.root)
        for tree, recipe in cases:
            (self.root / tree).unlink()
            shutil.copytree(owner / tree, self.root / tree)
        recipes, patches, files, categories = exporter.configuration(self.root)
        self.assertEqual([name for name, source in recipes], ['devel/meson', 'lang/llvm'])
        for tree, recipe in cases:
            selected = self.root / 'pkgsrc' / recipe / 'patches/patch-shared'
            target = os.readlink(selected)
            selected.unlink()
            with self.assertRaisesRegex(exporter.ExportError,
                    'Missing patch: pkgsrc/' + recipe + '/patches/patch-shared'):
                exporter.configuration(self.root)
            selected.symlink_to(target)

    def test_tsv_and_unfinished_record_grammar(self):
        (self.root / 'input').write_bytes(b'copied')
        config = self.root / 'pkgsrc/export.conf'
        config.write_bytes(b'# comment\nfile\t\tinput\tCOPIED\nunknown\tignored-no-final-newline')
        self.fake_export()
        self.assertEqual((self.work / 'export/COPIED').read_bytes(), b'copied')
        config.write_bytes(b'file\tinput\tCOPIED\r\n')
        recipes, patches, files, categories = exporter.configuration(self.root)
        self.assertEqual(files[0][1], 'COPIED\r')

    def test_shell_globs_skip_hidden_recipes_but_copy_new_category_data(self):
        (self.root / 'pkgsrc/.ignored').mkdir()
        existing = self.root / 'pkgsrc/devel'
        (existing / '.ignored').mkdir(parents=True)
        (existing / '.note').write_text('ignored category check data')
        (self.upstream / 'devel').mkdir()
        new_category = self.root / 'pkgsrc/local'
        new_category.mkdir()
        (new_category / '.data').write_bytes(b'preserved by whole-category copy')
        self.fake_export()
        self.assertFalse((self.work / 'export/.ignored').exists())
        self.assertFalse((self.work / 'export/devel/.note').exists())
        self.assertEqual((self.work / 'export/local/.data').read_bytes(),
                         b'preserved by whole-category copy')

    def test_compatibility_launcher_accepts_basename_invocation(self):
        existing = self.work / 'existing'
        existing.mkdir()
        done = subprocess.run(['/bin/sh', 'prepare-pkgsrc.sh', str(existing)],
            cwd=HERE.parent, env={**os.environ, 'PY': sys.executable},
            capture_output=True, text=True)
        self.assertEqual(done.returncode, 2)
        self.assertIn('Destination already exists.', done.stderr)

    def test_cli_refuses_without_sdk_loading_or_child_execution(self):
        with mock.patch.dict(os.environ, {}, clear=True), \
                mock.patch('sys.stderr', new_callable=io.StringIO) as output, \
                mock.patch('subprocess.run', side_effect=AssertionError('unexpected child')):
            self.assertEqual(exporter.main([str(self.work / 'unadmitted'),
                '--sdk-source', '/not-opened', '--descriptor', '/not-opened',
                '--bootstrap-plan', '/not-opened']), 2)
            self.assertIn('SDK source-export controller is not available', output.getvalue())
        self.assertFalse((self.work / 'unadmitted').exists())

    def test_three_standalone_entries_refuse_unrelated_selectors(self):
        root = HERE.parents[1]
        entries = [[sys.executable, '-B', str(root / 'scripts/prepare-pkgsrc.py')],
                   ['/bin/sh', str(root / 'scripts/prepare-pkgsrc.sh')],
                   [sys.executable, '-B', str(root / 'probes/lxqt/prepare-pkgsrc.py')]]
        for number, entry in enumerate(entries):
            destination = self.work / ('refused-' + str(number))
            argv = entry + [str(destination), '--sdk-source', '/not-opened',
                            '--descriptor', '/not-opened', '--bootstrap-plan', '/not-opened']
            done = subprocess.run(argv, env={**os.environ, 'PY': sys.executable},
                                  capture_output=True, text=True)
            self.assertEqual(done.returncode, 2)
            self.assertIn('SDK source-export controller is not available', done.stderr)
            self.assertFalse(destination.exists())

    def test_real_git_archive_binary_apply_modes_and_links(self):
        git = self.selected.command('git')[0]

        def command(where, *words):
            return self.runner([git, '-C', str(where), *words])

        command(self.upstream, 'init', '-q')
        initial = bytes(range(256)) * 2
        changed = b'\0changed\xff' + initial[::-1]
        (self.upstream / 'binary').write_bytes(initial)
        (self.upstream / 'executable').write_bytes(b'#!/bin/sh\nexit 0\n')
        (self.upstream / 'executable').chmod(0o755)
        (self.upstream / 'link').symlink_to('plain')
        command(self.upstream, 'add', '.')
        command(self.upstream, '-c', 'user.name=Source Test', '-c',
                'user.email=source-test@example.invalid', '-c', 'commit.gpgsign=false',
                '-c', 'core.hooksPath=/dev/null', 'commit', '-qm', 'Finite source fixture')
        pin = command(self.upstream, 'rev-parse', 'HEAD').decode().strip()
        (self.upstream / 'binary').write_bytes(changed)
        patch = command(self.upstream, 'diff', '--binary', '--no-ext-diff', '--no-textconv', 'HEAD')
        self.assertIn(b'GIT binary patch', patch)
        (self.root / 'binary.patch').write_bytes(patch)
        (self.root / 'sources.tsv').write_text('binary.patch\t' + hashlib.sha256(patch).hexdigest() + '\n')
        (self.root / 'pkgsrc/export.conf').write_text('git-apply\tbinary.patch\tsources.tsv\n')
        (self.root / 'upstream').mkdir()
        (self.root / 'upstream/pkgsrc').symlink_to(self.upstream)
        command(self.root, 'init', '-q')
        command(self.root, 'update-index', '--add', '--cacheinfo', f'160000,{pin},upstream/pkgsrc')
        revision = exporter.export_pkgsrc(self.root, self.work / 'real',
            selection=self.selected, runner=self.runner, scratch=self.work / "real-scratch")
        self.assertEqual(revision, pin)
        self.assertEqual((self.work / 'real/binary').read_bytes(), changed)
        self.assertTrue((self.work / 'real/link').is_symlink())
        self.assertEqual(os.readlink(self.work / 'real/link'), 'plain')
        self.assertEqual(stat.S_IMODE((self.work / 'real/executable').stat().st_mode), 0o755)
        self.assertEqual((self.work / 'real/EMBERBSD-PKGSRC-REVISION').read_text(), pin + '\n')
        calls = [argv for argv, options in self.commands if 'apply' in argv]
        self.assertEqual(calls, [
            [git, '-C', str(self.work / 'real'), 'apply', '--check', str(self.root / 'binary.patch')],
            [git, '-C', str(self.work / 'real'), 'apply', str(self.root / 'binary.patch')]])

    def test_patch_empty_file_removal_is_causal(self):
        patch = b'--- a/plain\n+++ b/plain\n@@ -1,3 +0,0 @@\n-one\n-two\n-three\n'
        (self.root / 'remove.patch').write_bytes(patch)
        (self.root / 'pkgsrc/export.conf').write_text('patch\tremove.patch\n')
        self.fake_export()
        self.assertFalse((self.work / 'export/plain').exists())
        self.assertIn(['-f', '-E', '-d', str(self.work / 'export'), '-p1', '-F', '0'],
                      [argv[1:] for argv, options in self.commands if argv[0] == self.selected.command('patch')[0]])
        control = self.work / 'without-E'
        control.mkdir()
        (control / 'plain').write_bytes(b'one\ntwo\nthree\n')
        self.runner([self.selected.command('patch')[0], '-f', '-d', str(control), '-p1', '-F', '0'], input=patch)
        self.assertEqual((control / 'plain').read_bytes(), b'')

    def test_zero_fuzz_rejects_context_that_fuzz_one_accepts(self):
        patch = b'--- a/plain\n+++ b/plain\n@@ -1,3 +1,3 @@\n wrong\n-two\n+changed\n three\n'
        (self.root / 'fuzz.patch').write_bytes(patch)
        (self.root / 'pkgsrc/export.conf').write_text('patch\tfuzz.patch\n')
        with self.assertRaisesRegex(exporter.ExportError, 'Infrastructure patch does not apply'):
            self.fake_export()
        control = self.work / 'fuzz-one'
        control.mkdir()
        (control / 'plain').write_bytes(b'one\ntwo\nthree\n')
        self.runner([self.selected.command('patch')[0], '-f', '-E', '-d', str(control), '-p1', '-F', '1'], input=patch)
        self.assertEqual((control / 'plain').read_bytes(), b'one\nchanged\nthree\n')

    def test_archive_rejects_traversal_and_link_writes(self):
        for member_name, link in [('../escape', None), ('/escape', None), ('link/file', '../outside')]:
            with self.subTest(member=member_name):
                archive = self.work / 'unsafe.tar'
                with tarfile.open(archive, 'w') as stream:
                    if link:
                        symlink = tarfile.TarInfo('link')
                        symlink.type = tarfile.SYMTYPE
                        symlink.linkname = link
                        stream.addfile(symlink)
                    member = tarfile.TarInfo(member_name)
                    member.size = 1
                    stream.addfile(member, io.BytesIO(b'x'))
                with self.assertRaises(exporter.ExportError):
                    exporter.extract_archive(archive, self.work / 'unsafe')
        self.assertFalse((self.work / 'escape').exists())

    def test_child_status_retains_scratch_until_caller_cleanup(self):

        def fail_archive(argv, **kwargs):
            if 'archive' in argv:
                raise subprocess.CalledProcessError(42, argv)
            return self.runner(argv, **kwargs)

        with self.assertRaises(subprocess.CalledProcessError) as error:
            self.fake_export(runner=fail_archive)
        self.assertEqual(error.exception.returncode, 42)
        self.assertFalse((self.work / 'export').exists())
        self.assertTrue((self.work / 'export-scratch').is_dir())
        shutil.rmtree(self.work / 'export-scratch')  # Injected status has no live child.

    def test_copy_fault_and_signals_retain_archive_until_caller_cleanup(self):
        (self.root / 'input').write_bytes(b'copy')
        (self.root / 'pkgsrc/export.conf').write_text('file\tinput\tCOPIED\n')
        for name, error in [('copy', OSError('injected copy fault')),
                            ('interrupt', SystemExit(130)), ('terminate', SystemExit(143))]:
            with self.subTest(case=name), mock.patch.object(exporter, 'copy_file', side_effect=error):
                with self.assertRaises(type(error)):
                    self.fake_export(name)
                self.assertEqual((self.work / name / 'plain').read_bytes(), b'one\ntwo\nthree\n')
                self.assertTrue((self.work / (name + '-scratch') / 'pkgsrc.tar').is_file())
                shutil.rmtree(self.work / (name + '-scratch'))  # Test child already returned.


    def test_sdk_ownership_error_retains_partial_archive_for_outer_hold(self):
        def unproven_archive(argv, **kwargs):
            if 'archive' in argv:
                output = next(word[9:] for word in argv if word.startswith('--output='))
                Path(output).write_bytes(b'partial archive owned by unproven writer')
                raise ProcessOwnershipError(0, 'injected SDK error; no real child session')
            return self.runner(argv, **kwargs)

        with self.assertRaises(ProcessOwnershipError):
            self.fake_export(runner=unproven_archive)
        scratch = self.work / 'export-scratch'
        self.assertEqual((scratch / 'pkgsrc.tar').read_bytes(),
                         b'partial archive owned by unproven writer')
        self.assertFalse((self.work / 'export').exists())
        # This is an injected error with no real child. Only this outer test
        # controller now knows it can clean. The exporter never cleaned it.
        shutil.rmtree(scratch)
        self.assertFalse(scratch.exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
