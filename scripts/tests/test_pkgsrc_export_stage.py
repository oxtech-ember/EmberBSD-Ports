# SPDX-License-Identifier: BSD-2-Clause
"""Keep pkgsrc export fingerprints scoped to declared source inputs."""

import importlib.util
import shutil
from pathlib import Path
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


if __name__ == '__main__':
    unittest.main()
