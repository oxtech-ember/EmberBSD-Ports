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
    def test_direct_reader_refuses_interrupted_export(self):
        sdk = Path(os.environ['EMBERBSD_SDK_SOURCE'])
        sys.path.insert(0, str(sdk / 'src'))
        with tempfile.TemporaryDirectory(dir=os.environ['EMBERBSD_TEST_WORK']) as temp:
            root = Path(temp) / 'pkgsrc'
            (root / 'cat/pkg').mkdir(parents=True)
            (root / 'cat/pkg/Makefile').write_text('DISTNAME=fixture\n')
            (root.parent / '.pkgsrc-update-incomplete').write_text('interrupted\n')
            with self.assertRaisesRegex(ValueError, 'update is incomplete'):
                identity.effective_package_identity(root, 'cat/pkg', '1' * 40)

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

    def test_shared_tree_snapshot_matches_independent_recipe_reads(self):
        sdk = Path(os.environ['EMBERBSD_SDK_SOURCE'])
        sys.path.insert(0, str(sdk / 'src'))
        from emberbsd_sdk import inventory
        with tempfile.TemporaryDirectory(dir=os.environ['EMBERBSD_TEST_WORK']) as temp:
            root = Path(temp)
            for name in ('scripts', 'pkgsrc/cat/pkg/files', 'pkgsrc/cat/empty',
                         'pkgsrc/lang/llvm/files', 'upstream/pkgsrc', 'profiles/extra'):
                (root / name).mkdir(parents=True)
            shutil.copy(ROOT / 'scripts/prepare-pkgsrc.py', root / 'scripts')
            shutil.copy(ROOT / 'pkgsrc/lang/llvm/files/sdk_source.py', root / 'pkgsrc/lang/llvm/files')
            (root / 'pkgsrc/export.conf').write_text('recipe\tprofiles/extra\tcat/extra\n')
            (root / 'pkgsrc/cat/pkg/Makefile').write_text('DISTNAME=pkg\n')
            (root / 'pkgsrc/cat/empty/Makefile').write_text('DISTNAME=empty\n')
            (root / 'pkgsrc/lang/llvm/Makefile').write_text('DISTNAME=llvm\n')
            (root / 'profiles/extra/Makefile').write_text('DISTNAME=extra\n')
            data = root / 'pkgsrc/cat/pkg/files/data'
            data.write_text('untracked input\n')
            data.chmod(0o755)
            (root / 'pkgsrc/cat/pkg/files/link').symlink_to('data')
            (root / 'profiles/extra/link').symlink_to('../../pkgsrc/cat/pkg/files/data')
            sha = b'1' * 40
            def git(argv, *, env):
                return b'160000 ' + sha + b' 0\tupstream/pkgsrc\n' if 'ls-files' in argv else sha + b'\n'
            def legacy_tree(source):
                rows = inventory.snapshot_installed_tree(str(source))
                for relative, row in rows.items():
                    if row['kind'] == 'link':
                        target = (source / relative).resolve(strict=True)
                        if not target.is_relative_to(root) or not target.is_file():
                            raise ValueError('unsupported export source link')
                        row['target_sha256'] = inventory.sha256_file(str(target))
                return rows
            with patch.object(identity.subprocess, 'check_output', side_effect=git):
                sources = [root / 'profiles/extra', root / 'pkgsrc/cat/pkg',
                           root / 'pkgsrc/cat/empty', root / 'pkgsrc/lang/llvm']
                expected = {str(source.relative_to(root)): legacy_tree(source) for source in sources}
                expected['pkgsrc'] = legacy_tree(root / 'pkgsrc')
                with patch.object(inventory, 'snapshot_installed_tree', wraps=inventory.snapshot_installed_tree) as snapshots:
                    _, _, before, _ = identity.export_inputs(root, sys.executable, sdk)
                self.assertEqual(before['trees'], expected)
                self.assertCountEqual([Path(call.args[0]) for call in snapshots.call_args_list],
                                      [root / 'pkgsrc', root / 'profiles/extra'])
                data.write_text('modified input\n')
                _, _, after, _ = identity.export_inputs(root, sys.executable, sdk)
                self.assertNotEqual(before, after)
                data.unlink()
                with self.assertRaises((FileNotFoundError, ValueError)):
                    identity.export_inputs(root, sys.executable, sdk)
                (root / 'pkgsrc/cat/pkg/files/link').unlink()
                (root / 'profiles/extra/link').unlink()
                _, _, deleted, _ = identity.export_inputs(root, sys.executable, sdk)
                self.assertNotEqual(after, deleted)



class GitPackageIdentityTest(unittest.TestCase):
    """The API 3 identity is made of Git object ids; no export is written."""

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
        self.assertEqual(before['api'], 3)
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

    def test_mixed_case_package_identity(self):
        self.write(self.upstream / 'net/mDNSResponder/Makefile', 'DISTNAME=example\n')
        self.write(self.upstream / 'net/mDNSResponder/distinfo', 'archive-checksum\n')
        self.commit_upstream('mixed case package')
        record = self.current('net/mDNSResponder')
        self.assertEqual(record['package'], 'net/mDNSResponder')
        self.assertTrue(identity.equivalent_effective_package(record, record))
        with self.assertRaises(ValueError):
            self.current('net/../escape')

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

    def test_current_contract_and_scoped_sections(self):
        one = '--- a/cat/pkg/Makefile\n+++ b/cat/pkg/Makefile\n@@ -1 +1 @@\n-old\n+new\n'
        two = '--- a/cat/other/Makefile\n+++ b/cat/other/Makefile\n@@ -1 +1 @@\n-old\n+new\n'
        patchfile = self.root / 'patches/infra.patch'
        self.conf('patch\tpatches/infra.patch\n')
        self.write(patchfile, 'Prose preamble.\n\n' + one + two)
        first = self.current()
        self.assertEqual(set(first), {'api', 'package', 'effective_package_sha256', 'upstream'})
        self.assertEqual(first['api'], 3)
        self.assertTrue(identity.matches_current_git_package(first, first))
        self.assertTrue(identity.current_git_package(
            {'effective': first, 'owner_sha256': '0' * 64}, '0' * 64, self.current))
        self.write(patchfile, 'Prose preamble.\n\n' + one + two.replace('+new', '+other'))
        second = self.current()
        self.assertEqual(first, second)
        self.assertTrue(identity.matches_current_git_package(first, second))
        for retired in (dict(first, api=1), dict(first, api=2),
                        dict(first, legacy_api2_sha256=first['effective_package_sha256'])):
            self.assertFalse(identity.matches_current_git_package(retired, first))
            self.assertFalse(identity.current_git_package(
                {'effective': retired, 'owner_sha256': '0' * 64}, '0' * 64, self.current))
        for invalid in (dict(first, api=True), dict(first, effective_package_sha256='x'),
                        dict(first, extra=1), dict(first, upstream='bad')):
            self.assertFalse(identity.equivalent_effective_package(first, invalid))
            self.assertFalse(identity.matches_current_git_package(invalid, first))
        for changed in (one.replace('+new', '+changed'), one.replace('b/cat/pkg/Makefile', 'b/cat/pkg/options.mk'),
                        one + one, one + one.replace('+new', '+second'),
                        '--- /dev/null\n+++ b/cat/pkg/new.mk\n@@ -0,0 +1 @@\n+new\n',
                        '--- a/cat/pkg/new.mk\n+++ /dev/null\n@@ -1 +0,0 @@\n-old\n'):
            self.write(patchfile, changed + two)
            self.assertFalse(identity.equivalent_effective_package(first, self.current()), changed)
        self.write(patchfile, one + one.replace('+new', '+second'))
        ordered = self.current()
        self.write(patchfile, one.replace('+new', '+second') + one)
        self.assertFalse(identity.equivalent_effective_package(ordered, self.current()))

    def test_whole_blob_hashes_are_batched(self):
        self.write(self.root / 'patches/a.patch', 'diff --git a/a b/a\n')
        self.write(self.root / 'patches/b.patch', 'Binary files differ\n')
        self.conf('patch\tpatches/a.patch\npatch\tpatches/b.patch\n')
        with patch.object(identity, '_hash_objects', wraps=identity._hash_objects) as hashes:
            self.current()
        batches = [[p.name for p in call.args[2]] for call in hashes.call_args_list]
        self.assertEqual(batches, [['a.patch', 'b.patch']])

    def test_real_cross_patch_is_sectionable(self):
        data = (ROOT / 'profiles/common-build-tools/patches/pkgsrc-cross-packages.patch').read_bytes()
        sections = identity._plain_patch_sections(data)
        self.assertIsNotNone(sections)
        self.assertGreater(len(sections), 1)

    def test_legacy_payload_requires_exact_recorded_identity(self):
        import hashlib
        import json
        old = b'old configuration\n'
        row = {'kind': 'file', 'mode': 0o644, 'size': len(old),
               'sha256': hashlib.sha256(old).hexdigest()}
        old_snapshot = {'api': 1, 'upstream': '1' * 40,
                        'files': {'pkgsrc/export.conf': row['sha256']},
                        'trees': {'pkgsrc': {'export.conf': row}}}
        digest = hashlib.sha256(json.dumps(old_snapshot, sort_keys=True,
            separators=(',', ':')).encode()).hexdigest()
        current = {'api': 1, 'upstream': '1' * 40,
                   'files': {'pkgsrc/export.conf': 'changed', 'new.patch': 'added'},
                   'trees': {'pkgsrc': {'export.conf': dict(row, sha256='changed')}}}
        changes = {'pkgsrc/export.conf': (old, 0o644, True),
                   'new.patch': (None, None, False)}
        self.assertEqual(identity.reconstruct_legacy_payload(current, changes, digest), old_snapshot)
        with self.assertRaisesRegex(ValueError, 'do not match'):
            identity.reconstruct_legacy_payload(current, changes, '0' * 64)
        with self.assertRaisesRegex(ValueError, 'unsafe'):
            identity.reconstruct_legacy_payload(current, {'../escape': (old, 0o644, True)}, digest)

    def test_gnu_diff_sections_require_matching_names(self):
        data = (ROOT / 'profiles/common-build-tools/patches/pkgsrc-bmake-executable-path.patch').read_bytes()
        sections = identity._update_patch_sections(data)
        self.assertIsNotNone(sections)
        self.assertIn(['devel/bmake/Makefile', 'devel/bmake/Makefile'], [row[0] for row in sections])
        self.assertIsNone(identity._update_patch_sections(
            b'diff -ruN a/cat/pkg/a b/cat/pkg/b\n'
            b'--- a/cat/pkg/a\n+++ b/cat/pkg/a\n@@ -1 +1 @@\n-old\n+new\n'))

    def test_git_wrappers_reject_ambiguous_changes(self):
        hunk = b'--- a/cat/pkg/a\n+++ b/cat/pkg/a\n@@ -1 +1 @@\n-old\n+new\n'
        for wrapper in (
            b'diff --git a/cat/pkg/a b/cat/pkg/b\n',
            b'diff --git a/cat/pkg/a b/cat/pkg/a\nindex bad..1234567 100644\n',
            b'diff --git a/cat/pkg/a b/cat/pkg/a\nold mode 100644\nnew mode 100755\n',
            b'diff --git "a/cat/pkg/a" "b/cat/pkg/a"\n',
        ):
            with self.subTest(wrapper=wrapper):
                self.assertIsNone(identity._update_patch_sections(wrapper + hunk))

    def test_parser_payload_and_conservative_fallback(self):
        misleading = (b'--- a/cat/pkg/Makefile\n+++ b/cat/pkg/Makefile\n@@ -1,2 +1,2 @@\n'
                      b'--- a/cat/other/Makefile\n+++ b/cat/other/Makefile\n context\n')
        sections = identity._plain_patch_sections(misleading)
        self.assertEqual(len(sections), 1)
        self.assertEqual(sections[0][0], ['cat/pkg/Makefile', 'cat/pkg/Makefile'])
        for data in (b'diff --git a/a b/a\nold mode 100644\n', b'Index: file\n',
                     b'GIT binary patch\n', b'Binary files differ\n', b'old mode 100644\n',
                     b'rename from a\nrename to b\n',
                     b'1c\nfoo\n.\n--- a/cat/pkg/Makefile\n+++ b/cat/pkg/Makefile\n@@ -1 +1 @@\n-x\n+y\n',
                     b'--- a/cat/pkg/Makefile\n+++ b/cat/pkg/Makefile\n@@ -2,2 +2 @@\n-x\n+y\n',
                     b'--- a/a\n+++ b/a\n@@ -1 +1 @@\n-x\n+y\nunknown\n'):
            self.assertIsNone(identity._plain_patch_sections(data), data)
            patchfile = self.root / 'patches/infra.patch'
            patchfile.write_bytes(data)
            self.conf('patch\tpatches/infra.patch\n')
            before = self.current()
            patchfile.write_bytes(data + b'changed\n')
            self.assertFalse(identity.equivalent_effective_package(before, self.current()))

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
