# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Exercise canonical-export identity with a small synthetic overlay."""

import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('identity', ROOT / 'scripts/pkgsrc-source-identity.py')
identity = importlib.util.module_from_spec(spec)
spec.loader.exec_module(identity)


class IdentityTest(unittest.TestCase):
    def test_effective_package_identity(self):
        sdk = Path(__import__('os').environ['EMBERBSD_SDK_SOURCE'])
        sys.path.insert(0, str(sdk / 'src'))
        work = Path(__import__('os').environ['EMBERBSD_TEST_WORK'])
        with tempfile.TemporaryDirectory(dir=work) as temp:
            root = Path(temp)
            package = root / 'cat/pkg'
            (package / 'patches').mkdir(parents=True)
            (package / 'Makefile').write_text('DISTNAME=example\n')
            (package / 'distinfo').write_text('archive-checksum\n')
            (package / 'patches/patch-a').write_text('patch\n')
            (package / 'DESCR').write_text('description\n')
            before = identity.effective_package_identity(root, 'cat/pkg', '1' * 40)
            other = root / 'cat/other'
            other.mkdir()
            (other / 'Makefile').write_text('unrelated\n')
            (package / 'DESCR').write_text('unrelated description change\n')
            after = identity.effective_package_identity(root, 'cat/pkg', '2' * 40)
            self.assertEqual(before['effective_package_sha256'], after['effective_package_sha256'])
            self.assertNotEqual(before['upstream'], after['upstream'])
            self.assertTrue(identity.equivalent_effective_package(before, after))
            self.assertFalse(identity.equivalent_effective_package(before, {**after, 'upstream': 'bad'}))
            for file in ('Makefile', 'distinfo', 'patches/patch-a'):
                path = package / file
                original = path.read_text()
                path.write_text(original + 'changed\n')
                changed = identity.effective_package_identity(root, 'cat/pkg', '2' * 40)
                self.assertNotEqual(before['effective_package_sha256'], changed['effective_package_sha256'])
                self.assertFalse(identity.equivalent_effective_package(before, changed))
                path.write_text(original)

    def test_overlay_change_and_gitlink(self):
        sdk = Path(__import__('os').environ['EMBERBSD_SDK_SOURCE'])
        work = Path(__import__('os').environ['EMBERBSD_TEST_WORK'])
        with tempfile.TemporaryDirectory(dir=work) as temp:
            root = Path(temp)
            for name in ('scripts', 'pkgsrc/cat/pkg', 'pkgsrc/lang/llvm/files', 'upstream/pkgsrc'):
                (root / name).mkdir(parents=True)
            shutil.copy(ROOT / 'scripts/prepare-pkgsrc.py', root / 'scripts')
            shutil.copy(ROOT / 'pkgsrc/lang/llvm/files/sdk_source.py', root / 'pkgsrc/lang/llvm/files')
            (root / 'pkgsrc/lang/llvm/Makefile').write_text('DISTNAME=llvm\n')
            (root / 'pkgsrc/export.conf').write_text('')
            (root / 'pkgsrc/cat/pkg/Makefile').write_text('DISTNAME=example\n')
            sha = b'1' * 40
            def git(argv, *, env):
                self.assertNotIn('GIT_INDEX_FILE', env)
                self.assertEqual(env['GIT_NO_LAZY_FETCH'], '1')
                if 'ls-files' in argv:
                    return b'160000 ' + sha + b' 0\tupstream/pkgsrc\n'
                return sha + b'\n'
            with patch.dict('os.environ', {'GIT_INDEX_FILE': '/untrusted'}), \
                    patch.object(identity.subprocess, 'check_output', side_effect=git):
                before = identity.identity(root, 'cat/pkg', sys.executable, sdk)
                self.assertEqual(before, identity.identity(root, 'cat/pkg', sys.executable, sdk))
                (root / 'pkgsrc/cat/pkg/Makefile').write_text('DISTNAME=changed\n')
                self.assertNotEqual(before, identity.identity(root, 'cat/pkg', sys.executable, sdk))
                overlay = root / 'overlay.patch'
                overlay.write_text('first patch\n')
                (root / 'pkgsrc/export.conf').write_text('patch\toverlay.patch\n')
                with_patch = identity.identity(root, 'cat/pkg', sys.executable, sdk)
                overlay.write_text('changed patch\n')
                self.assertNotEqual(with_patch, identity.identity(root, 'cat/pkg', sys.executable, sdk))
                sha = b'2' * 40
                self.assertNotEqual(before['upstream'], identity.identity(root, 'cat/pkg', sys.executable, sdk)['upstream'])
                other = root / 'other-sdk/src/emberbsd_sdk'
                other.mkdir(parents=True)
                (other / '__init__.py').write_text('API_VERSION = 1\n')
                with self.assertRaisesRegex(ValueError, 'different SDK'):
                    identity.identity(root, 'cat/pkg', sys.executable, root / 'other-sdk')
                with self.assertRaisesRegex(ValueError, 'absolute executable'):
                    identity.identity(root, 'cat/pkg', 'git', sdk)



class GitPackageIdentityTest(unittest.TestCase):
    """The API 2 identity is made of Git object ids; no export is written."""

    def setUp(self):
        self.git = os.environ.get('EXPORT_TEST_GIT')
        if not self.git:
            self.skipTest('Set EXPORT_TEST_GIT to the selected Git executable.')
        work = Path(os.environ['EMBERBSD_TEST_WORK'])
        self.temp = tempfile.TemporaryDirectory(dir=work)
        self.root = Path(self.temp.name) / 'ports'
        self.upstream = self.root / 'upstream/pkgsrc'
        for name in ('scripts', 'pkgsrc', 'patches'):
            (self.root / name).mkdir(parents=True)
        shutil.copy(ROOT / 'scripts/prepare-pkgsrc.py', self.root / 'scripts')
        (self.root / 'pkgsrc/export.conf').write_text('')
        self.upstream.mkdir(parents=True)
        files = {'cat/pkg/Makefile': 'DISTNAME=example\n', 'cat/pkg/distinfo': 'SHA512 (a.tar) = 0\n',
                 'cat/pkg/patches/patch-a': 'patch\n', 'cat/pkg/DESCR': 'description\n',
                 'cat/pkg/options.mk': 'OPTIONS\n', 'cat/pkg/files/extra.c': 'int x;\n',
                 'cat/other/Makefile': 'DISTNAME=other\n', 'cat/Makefile': 'SUBDIR+=pkg\n',
                 'mk/bsd.pkg.mk': 'upstream\n'}
        for name, text in files.items():
            self.write(self.upstream / name, text)
        self.run_git(self.upstream, 'init', '-q')
        self.commit_upstream('initial')

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def write(path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def run_git(self, directory, *args):
        env = {'PATH': '/usr/bin:/bin', 'HOME': str(self.root.parent), 'GIT_CONFIG_NOSYSTEM': '1',
               'GIT_AUTHOR_NAME': 'Test', 'GIT_AUTHOR_EMAIL': 'test@example.invalid',
               'GIT_COMMITTER_NAME': 'Test', 'GIT_COMMITTER_EMAIL': 'test@example.invalid'}
        return subprocess.run([self.git, '-C', str(directory), *args], env=env, check=True,
                              stdout=subprocess.PIPE).stdout.decode().strip()

    def commit_upstream(self, message):
        self.run_git(self.upstream, 'add', '-A')
        self.run_git(self.upstream, 'commit', '-q', '-m', message)
        head = self.run_git(self.upstream, 'rev-parse', 'HEAD')
        if not (self.root / '.git').exists():
            self.run_git(self.root, 'init', '-q')
        self.run_git(self.root, 'update-index', '--add', '--cacheinfo', '160000,' + head + ',upstream/pkgsrc')
        return head

    def current(self, package='cat/pkg'):
        return identity.git_package_identity(self.root, package, self.git)

    def conf(self, text):
        (self.root / 'pkgsrc/export.conf').write_text(text)

    def assertChanged(self, before, message):
        after = self.current()
        self.assertNotEqual(before['effective_package_sha256'], after['effective_package_sha256'], message)
        self.assertFalse(identity.equivalent_effective_package(before, after), message)
        return after

    def test_same_inputs_same_identity(self):
        before = self.current()
        self.assertEqual(before['api'], 2)
        self.assertEqual(before, self.current())
        # A second process computes the same identity from the same objects.
        code = ('import importlib.util, json, sys; '
                'spec = importlib.util.spec_from_file_location("i", sys.argv[1]); '
                'm = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); '
                'print(json.dumps(m.git_package_identity(sys.argv[2], "cat/pkg", sys.argv[3])))')
        other = subprocess.run([sys.executable, '-B', '-c', code, str(ROOT / 'scripts/pkgsrc-source-identity.py'),
                                str(self.root), self.git], check=True, stdout=subprocess.PIPE).stdout
        self.assertEqual(before, __import__('json').loads(other))
        self.assertTrue(identity.current_git_package(
            {'effective': before, 'owner_sha256': '0' * 64}, '0' * 64, self.current))
        self.assertFalse(identity.current_git_package(
            {'effective': before, 'owner_sha256': '0' * 64}, '1' * 64, self.current))
        self.assertFalse(identity.current_git_package(
            {'effective': dict(before, api=1), 'owner_sha256': '0' * 64}, '0' * 64, self.current))

    def test_unrelated_upstream_change_keeps_identity(self):
        before = self.current()
        self.write(self.upstream / 'cat/other/Makefile', 'DISTNAME=changed\n')
        self.write(self.upstream / 'cat/pkg/DESCR', 'changed description\n')
        self.write(self.upstream / 'mk/bsd.pkg.mk', 'changed\n')
        self.commit_upstream('unrelated')
        after = self.current()
        self.assertNotEqual(before['upstream'], after['upstream'])
        self.assertTrue(identity.equivalent_effective_package(before, after))

    def test_dependent_upstream_paths_change_identity(self):
        before = self.current()
        for name in ('Makefile', 'distinfo', 'patches/patch-a', 'options.mk', 'files/extra.c',
                     'Makefile.common', 'patches/patch-new', 'new.mk'):
            path = self.upstream / 'cat/pkg' / name
            original = path.read_text() if path.exists() else None
            self.write(path, (original or '') + 'changed\n')
            self.commit_upstream('change ' + name)
            self.assertChanged(before, name)
            if original is None:
                path.unlink()
            else:
                path.write_text(original)
            self.commit_upstream('restore ' + name)
            self.assertTrue(identity.equivalent_effective_package(before, self.current()), name)
        os.chmod(self.upstream / 'cat/pkg/files/extra.c', 0o755)
        self.commit_upstream('mode')
        self.assertChanged(before, 'mode')

    def test_overlay_recipe_patch_file_and_infrastructure_patch(self):
        before = self.current()
        overlay = self.root / 'recipes/pkg'
        self.write(overlay / 'Makefile', 'DISTNAME=example\n')
        self.write(overlay / 'distinfo', 'SHA512 (a.tar) = 0\n')
        self.conf('recipe\trecipes/pkg\tcat/pkg\n')
        with_overlay = self.assertChanged(before, 'overlay')
        # Uncommitted overlay edits count.
        self.write(overlay / 'Makefile', 'DISTNAME=edited\n')
        edited = self.assertChanged(with_overlay, 'overlay edit')
        os.chmod(overlay / 'Makefile', 0o755)
        self.assertChanged(edited, 'overlay mode')
        self.conf('')
        self.assertEqual(before, self.current())
        self.write(self.root / 'patches/patch-b', 'recipe patch\n')
        self.conf('recipe-patch\tpatches/patch-b\tcat/pkg\tpatch-b\n')
        with_patch = self.assertChanged(before, 'recipe patch')
        self.write(self.root / 'patches/patch-b', 'changed recipe patch\n')
        self.assertChanged(with_patch, 'recipe patch edit')
        self.write(self.root / 'patches/extra.c', 'int y;\n')
        self.conf('file\tpatches/extra.c\tcat/pkg/files/added.c\n')
        self.assertChanged(before, 'exported file')
        self.conf('file\tpatches/extra.c\tcat/other/files/added.c\n')
        self.assertEqual(before, self.current())
        self.write(self.root / 'patches/infra.patch',
                   '--- a/cat/pkg/Makefile\n+++ b/cat/pkg/Makefile\n@@ -1 +1 @@\n-DISTNAME=example\n+DISTNAME=patched\n')
        self.conf('patch\tpatches/infra.patch\n')
        with_infra = self.assertChanged(before, 'infrastructure patch')
        self.write(self.root / 'patches/infra.patch',
                   '--- a/cat/pkg/Makefile\n+++ b/cat/pkg/Makefile\n@@ -1 +1 @@\n-DISTNAME=example\n+DISTNAME=other\n')
        self.assertChanged(with_infra, 'infrastructure patch edit')
        self.write(self.root / 'patches/infra.patch',
                   '--- a/cat/other/Makefile\n+++ b/cat/other/Makefile\n@@ -1 +1 @@\n-DISTNAME=other\n+DISTNAME=x\n')
        self.assertEqual(before, self.current())
        self.write(self.root / 'patches/infra.patch', 'no file names\n')
        self.assertChanged(before, 'unknown patch targets are included')

    def test_rows_equal_the_canonical_export(self):
        patch_tool = os.environ.get('EXPORT_TEST_PATCH')
        if not patch_tool:
            self.skipTest('Set EXPORT_TEST_PATCH to the selected patch executable.')
        overlay = self.root / 'pkgsrc/new/tool'
        self.write(overlay / 'Makefile', 'DISTNAME=tool\n')
        self.write(overlay / 'distinfo', 'SHA512 (t.tar) = 0\n')
        self.write(self.root / 'patches/patch-b', '--- x.orig\n+++ x\n')
        self.write(self.root / 'patches/added.c', 'int y;\n')
        self.conf('recipe-patch\tpatches/patch-b\tcat/pkg\tpatch-b\n'
                  'file\tpatches/added.c\tcat/pkg/files/added.c\n')
        exported = Path(self.temp.name) / 'export'
        subprocess.run([sys.executable, '-B', str(self.root / 'scripts/prepare-pkgsrc.py'), str(exported),
                        '--git', self.git, '--patch', patch_tool], check=True, stdout=subprocess.DEVNULL)
        for package in ('cat/pkg', 'new/tool'):
            rows = identity.git_package_inputs(self.root, package, self.git)
            self.assertEqual(rows['infrastructure_patches'], [])
            self.assertEqual(rows['tree'], identity.exported_package_rows(exported, package, self.git), package)


if __name__ == '__main__':
    unittest.main()
