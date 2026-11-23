# SPDX-License-Identifier: BSD-2-Clause
"""Keep pkgsrc export fingerprints scoped to declared source inputs."""

import importlib.util
import os
import shutil
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


stage = load(ROOT / 'scripts/pkgsrc-export-stage.py', 'pkgsrc_export_stage_test')


class ExportStageInputTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='pkgsrc-export-stage.')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve() / 'ports'
        (self.root / 'scripts').mkdir(parents=True)
        shutil.copyfile(ROOT / 'scripts/prepare-pkgsrc.py',
                        self.root / 'scripts/prepare-pkgsrc.py')
        (self.root / 'pkgsrc').mkdir()
        (self.root / 'pkgsrc/export.conf').write_text(
            'recipe\tprofiles/test-recipe\tcat/example\n'
            'patch\tprofiles/infrastructure.patch\n'
            'git-apply\tprofiles/git-apply.patch\tprofiles/manifests/git-apply.manifest\n'
            'recipe-patch\tprofiles/patches/patch-example\tcat/example\tpatch-example\n'
            'file\tprofiles/exported.txt\tshare/example\n')
        for name in ('profiles/test-recipe/patches', 'profiles/manifests',
                     'profiles/patches'):
            (self.root / name).mkdir(parents=True)
        (self.root / 'profiles/test-recipe/Makefile').write_text('PKGNAME=example\n')
        # Deliberately malformed for full export validation. Fingerprint path
        # discovery must not validate every recipe's patch roster.
        (self.root / 'profiles/test-recipe/patches/patch-unlisted').write_text('bad\n')
        for name in ('profiles/infrastructure.patch', 'profiles/git-apply.patch',
                     'profiles/manifests/git-apply.manifest',
                     'profiles/patches/patch-example', 'profiles/exported.txt'):
            (self.root / name).write_text('input\n')

    def test_shared_distinfo_checks_the_selected_patch_subset(self):
        exporter = stage._exporter(self.root)
        owner = self.root / 'pkgsrc/category/library'
        tools = self.root / 'pkgsrc/category/tools'
        for package in (owner, tools):
            (package / 'patches').mkdir(parents=True)
            (package / 'Makefile').touch()
        records = []
        for name in ('patch-library', 'patch-tools'):
            path = owner / 'patches' / name
            path.write_text(name + '\n')
            records.append(f'SHA1 ({name}) = {exporter.patch_sha1(path)}\n')
        (owner / 'distinfo').write_text(''.join(records))
        (tools / 'distinfo').symlink_to('../library/distinfo')
        selected = tools / 'patches/patch-tools'
        selected.symlink_to('../../library/patches/patch-tools')
        exporter.check_recipe(tools, 'tools', self.root)
        selected.unlink()
        selected.write_text('changed\n')
        with self.assertRaisesRegex(exporter.ExportError, 'Patch checksum differs'):
            exporter.check_recipe(tools, 'tools', self.root)

    def test_input_discovery_does_not_run_full_recipe_validation(self):
        exporter = stage._exporter(self.root)
        with mock.patch.object(exporter, 'check_recipe', side_effect=AssertionError), \
             mock.patch.object(exporter, 'check_tree_links', side_effect=AssertionError), \
             mock.patch.object(stage, '_exporter', return_value=exporter):
            paths = stage.input_paths(self.root)
        self.assertTrue({'pkgsrc', 'scripts/prepare-pkgsrc.py',
                         'profiles/test-recipe', 'profiles/infrastructure.patch',
                         'profiles/git-apply.patch',
                         'profiles/manifests/git-apply.manifest',
                         'profiles/patches/patch-example', 'profiles/exported.txt'}
                        <= set(paths))
        with self.assertRaisesRegex(exporter.ExportError, 'Undeclared patch'):
            exporter.configuration(self.root)

    def test_fingerprint_rejects_dirty_untracked_and_ignored_inputs(self):
        tool = self.root / 'patch-tool'
        tool.write_text('#!/bin/sh\n')
        tool.chmod(0o755)
        for status in (b' M profiles/test-recipe/Makefile\0',
                       b'?? profiles/manifests/new.manifest\0',
                       b'!! profiles/exported.txt\0'):
            with self.subTest(status=status), \
                 mock.patch.object(stage, '_executable', side_effect=lambda path, role: path), \
                 mock.patch.object(stage, '_git', return_value=status):
                with self.assertRaisesRegex(ValueError, 'uncommitted pkgsrc export inputs'):
                    stage.fingerprint_inputs('/git', str(tool), self.root)

    def test_batched_tree_ids_match_individual_git_lookups_and_reject_missing_paths(self):
        git = os.environ.get('EXPORT_TEST_GIT')
        if not git:
            self.skipTest('EXPORT_TEST_GIT is required for Git object identity regression')
        (self.root / 'profiles/with space').write_text('spaced path\n')
        subprocess.run([git, 'init', '-q', str(self.root)], check=True)
        subprocess.run([git, '-C', str(self.root), 'add', '-A'], check=True)
        subprocess.run([git, '-C', str(self.root), '-c', 'user.name=Test',
                        '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'fixture'],
                       check=True)
        paths = ['pkgsrc', 'profiles/test-recipe',
                 'profiles/manifests/git-apply.manifest', 'profiles/with space']
        expected = {
            path: subprocess.run([git, '-C', str(self.root), 'rev-parse', '--verify',
                                  'HEAD:' + path], stdout=subprocess.PIPE,
                                 check=True).stdout.decode('ascii').strip()
            for path in paths}
        calls = []
        run = subprocess.run
        def counted_run(*args, **kwargs):
            calls.append(args[0])
            return run(*args, **kwargs)
        with mock.patch.object(stage.subprocess, 'run', side_effect=counted_run):
            self.assertEqual(stage._object_ids(git, self.root, paths), expected)
        self.assertEqual(len(calls), 1)
        with self.assertRaisesRegex(ValueError, 'missing from HEAD'):
            stage._object_ids(git, self.root, paths + ['profiles/not-present'])

    def test_fingerprint_ignores_only_metadata_excluded_from_export(self):
        git = os.environ['EXPORT_TEST_GIT']
        shutil.copyfile(ROOT / 'scripts/pkgsrc-source-identity.py',
                        self.root / 'scripts/pkgsrc-source-identity.py')
        (self.root / '.gitignore').write_text('.DS_Store\n__pycache__/\n._*\n')
        tool = self.root / 'patch-tool'
        tool.write_text('#!/bin/sh\n')
        tool.chmod(0o755)
        subprocess.run([git, 'init', '-q', str(self.root)], check=True)
        subprocess.run([git, '-C', str(self.root), 'add', '-Af'], check=True)
        subprocess.run([git, '-C', str(self.root), 'update-index', '--add',
                        '--cacheinfo', '160000,' + '1' * 40 + ',upstream/pkgsrc'], check=True)
        subprocess.run([git, '-C', str(self.root), '-c', 'user.name=Test',
                        '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'fixture'], check=True)
        before = stage.fingerprint_inputs(git, str(tool), self.root)
        for name in ('pkgsrc/.DS_Store', 'pkgsrc/__pycache__/cache.pyc',
                     'profiles/test-recipe/files/__pycache__/module.pyc',
                     'profiles/test-recipe/files/._resource'):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'local metadata')
        self.assertEqual(stage.fingerprint_inputs(git, str(tool), self.root), before)
        (self.root / 'profiles/test-recipe/new-source.c').write_text('int input;\n')
        with self.assertRaisesRegex(ValueError, 'new-source.c'):
            stage.fingerprint_inputs(git, str(tool), self.root)


if __name__ == '__main__':
    unittest.main()
