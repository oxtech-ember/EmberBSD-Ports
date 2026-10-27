#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD; AI-assisted finite exporter regressions.
"""Test export semantics with explicit host regression tools, never seed admission."""

import hashlib
import importlib.util
import io
import os
import re
from pathlib import Path
import stat
import shutil
import subprocess
import sys
import tarfile
import tempfile
import types
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
        self.work = Path(self.temporary.name).resolve()
        self.root = self.work / 'ports'
        (self.root / 'pkgsrc').mkdir(parents=True)
        (self.root / 'pkgsrc/export.conf').write_bytes(b'')
        self.upstream = self.work / 'upstream'
        self.upstream.mkdir()
        (self.upstream / 'plain').write_bytes(b'one\ntwo\nthree\n')
        self.selected = fixture.TestSelection()
        self.commands = []
        help_result = subprocess.run([*self.selected.command('patch'), '--help'],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.patch_help = help_result.stdout

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

    def test_gnu_recipes_use_canonical_patch_checksums(self):
        owner = HERE.parents[1]
        for name in ('devel/diffutils', 'sysutils/findutils'):
            source = owner / 'pkgsrc' / name
            with self.subTest(recipe=name):
                exporter.check_recipe(source, name, owner)

    def test_recipe_patch_rcs_changes_keep_digest_but_raw_or_changed_body_refuse(self):
        source = self.root / 'pkgsrc/devel/patch-checksum'
        (source / 'patches').mkdir(parents=True)
        (source / 'Makefile').write_text('PKGNAME=patch-checksum-1\n')
        path, info = source / 'patches/patch-value', source / 'distinfo'
        body = b'\n--- value.orig\n+++ value\n@@ -1 +1 @@\n-before\n+after\n'
        path.write_bytes(b'$NetBSD: first RCS record $\n' + body)
        expected = hashlib.sha1(body).hexdigest()
        info.write_text('SHA1 (patch-value) = ' + expected + '\n')
        exporter.check_recipe(source, 'patch-checksum', self.root)
        info.write_text('SHA1 (patch-value) = ' + hashlib.sha1(path.read_bytes()).hexdigest() + '\n')
        with self.assertRaisesRegex(exporter.ExportError, 'Patch checksum differs'):
            exporter.check_recipe(source, 'patch-checksum', self.root)
        info.write_text('SHA1 (patch-value) = ' + expected + '\n')
        path.write_bytes(b'$NetBSD: changed RCS record $\n' + body)
        exporter.check_recipe(source, 'patch-checksum', self.root)
        path.write_bytes(b'$NetBSD: changed RCS record $\n' + body.replace(b'+after', b'+changed'))
        with self.assertRaisesRegex(exporter.ExportError, 'Patch checksum differs'):
            exporter.check_recipe(source, 'patch-checksum', self.root)

    def test_vala_infrastructure_patches_compose_without_fuzz(self):
        owner = HERE.parents[1]
        names = ['valadoc-option', 'array-termination', 'dbus-fd-exhaustion']
        paths = [owner / ('profiles/common-build-tools/patches/pkgsrc-vala-' + name + '.patch')
                 for name in names]
        configured = [line.split('\t')[1] for line in
                      (owner / 'pkgsrc/export.conf').read_text().splitlines()
                      if line.startswith('patch\t') and 'pkgsrc-vala-' in line]
        self.assertEqual(configured, [str(path.relative_to(owner)) for path in paths])
        tree = self.work / 'vala-composition'
        recipe = tree / 'lang/vala'
        recipe.parent.mkdir(parents=True)
        shutil.copytree(owner / 'upstream/pkgsrc/lang/vala', recipe)
        (tree / 'mk/defaults').mkdir(parents=True)
        shutil.copyfile(owner / 'upstream/pkgsrc/mk/defaults/options.description',
                        tree / 'mk/defaults/options.description')

        def apply(target, data):
            return self.runner(self.selected.command('patch') +
                ('-f', '-E', '-d', str(target), '-p1', '-F', '0'), input=data)

        for path in paths[:2]:
            self.assertNotIn(b'fuzz', apply(tree, path.read_bytes()))
        before = (recipe / 'distinfo').read_bytes()
        fixed = paths[2].read_bytes()
        context = b' SHA1 (patch-tests_generics_arrays.c-expected) = e5faf542e07fd5786c6dd3f1622816f0857427e4\n'
        self.assertEqual(fixed.count(context), 1)
        wrong = fixed.replace(context,
            b' SHA1 (patch-tests_generics_arrays.c-expected) = ' + b'0' * 40 + b'\n')
        start = wrong.index(b'--- a/lang/vala/distinfo\n')
        end = wrong.index(b'--- /dev/null\n', start)
        negative = self.work / 'vala-wrong-context'
        (negative / 'lang/vala').mkdir(parents=True)
        (negative / 'lang/vala/distinfo').write_bytes(before)
        with self.assertRaises(subprocess.CalledProcessError):
            apply(negative, wrong[start:end])
        self.assertEqual((negative / 'lang/vala/distinfo').read_bytes(), before)
        self.assertTrue((negative / 'lang/vala/distinfo.rej').is_file())
        output = apply(tree, fixed)
        self.assertNotIn(b'fuzz', output)
        self.assertNotIn(b'offset', output)
        exporter.check_recipe(recipe, 'lang/vala', tree)
        added = b'SHA1 (patch-tests_dbus_filedescriptor-errors.test) = 141dcfbce89d244899efe53c880e36a91130ba97\n'
        self.assertEqual((recipe / 'distinfo').read_bytes().replace(added, b''), before)
        self.assertEqual((recipe / 'Makefile').read_bytes().count(
            b'TEST_DEPENDS+=\tdbus>=1.16.2:../../sysutils/dbus\n'), 1)

    def test_numeric_owner_patch_composes_after_pkg_install_revision_patches(self):
        owner = HERE.parents[1]
        target_name = b'pkgtools/pkg_install/Makefile'
        numeric_path = 'profiles/common-build-tools/patches/pkgsrc-numeric-package-owners.patch'
        tree = self.work / 'numeric-owner-patch'
        target = tree / target_name.decode()
        target.parent.mkdir(parents=True)
        shutil.copyfile(owner / 'upstream/pkgsrc' / target_name.decode(), target)

        preceding = []
        for line in (owner / 'pkgsrc/export.conf').read_text().splitlines():
            if not line or line.startswith('#'):
                continue
            fields = line.split('\t')
            if fields[0] != 'patch':
                continue
            if fields[1] == numeric_path:
                break
            data = (owner / fields[1]).read_bytes()
            section = next((part for part in re.split(rb'(?=^--- a/)', data, flags=re.M)
                            if part.startswith(b'--- a/' + target_name + b'\n')), None)
            if section is not None:
                preceding.append((fields[1], section))
        argv = self.selected.command('patch') + (
            '-f', '-E', '-d', str(tree), '-p1', '-F', '0', '-V', 'none')
        for name, patch in preceding:
            with self.subTest(patch=name):
                self.runner(argv, input=patch)

        before = target.read_bytes()
        self.assertIn(b'PKGREVISION=\t\t7\n', before)
        numeric_data = (owner / numeric_path).read_bytes()
        section = next(part for part in re.split(rb'(?=^--- a/)', numeric_data, flags=re.M)
                       if part.startswith(b'--- a/' + target_name + b'\n'))
        try:
            output = self.runner(argv, input=section)
        except subprocess.CalledProcessError as error:
            diagnostic = (error.stdout or b'') + (error.stderr or b'')
            self.fail('numeric owner patch did not apply: ' +
                      diagnostic.decode(errors='replace'))
        self.assertNotIn(b'fuzz', output)
        self.assertNotIn(b'offset', output)

        old = b'MAKE_ENV+=\t\tSED=${SED:Q}\n\nPKG_DBDIR?='
        new = (b'MAKE_ENV+=\t\tSED=${SED:Q}\n\n'
               b'# Keep nested static-library builds on the selected archive tools.\n'
               b'MAKE_FLAGS+=\t\tAR=${AR:Q} RANLIB=${RANLIB:Q}\n'
               b'CONFIGURE_ENV+=\t\tAR=${AR:Q} RANLIB=${RANLIB:Q}\n\n\n'
               b'PKG_DBDIR?=')
        self.assertEqual(before.count(old), 1)
        expected = before.replace(b'PKGREVISION=\t\t7\n',
                                  b'PKGREVISION=\t\t8\n', 1).replace(old, new, 1)
        self.assertEqual(target.read_bytes(), expected)

    def test_nss_infrastructure_hunk_retains_three_line_context(self):
        owner = HERE.parents[1]
        path = owner / 'profiles/common-build-tools/patches/pkgsrc-nss-cross-host-tools.patch'
        fixed = path.read_bytes()
        start = fixed.index(b'@@ -33,9 +33,14 @@\n')
        end = fixed.index(b'diff --git ', start)
        hunk = fixed[start:end]
        context = (b' MAKE_FLAGS+=\t\tNATIVE_EXTRA_SHARED_LIBS=\n'
                   b' \n'
                   b' NSS_CPU_ARCH.aarch64eb=\t\taarch64\n')
        self.assertTrue(hunk.endswith(context))
        wrong = hunk.replace(b' NSS_CPU_ARCH.aarch64eb=\t\taarch64\n',
                             b' NSS_CPU_ARCH.aarch64eb=\t\tnot-aarch64\n')
        header = b'--- a/devel/nss/Makefile\n+++ b/devel/nss/Makefile\n'
        before = (owner / 'upstream/pkgsrc/devel/nss/Makefile').read_bytes()
        old_lines = b''.join(line[1:] for line in hunk.splitlines(keepends=True)[1:]
                             if line.startswith((b' ', b'-')))
        new_lines = b''.join(line[1:] for line in hunk.splitlines(keepends=True)[1:]
                             if line.startswith((b' ', b'+')))
        self.assertEqual(before.count(old_lines), 1)
        for name, data in [('wrong', wrong), ('fixed', hunk)]:
            tree = self.work / ('nss-context-' + name)
            directory = tree / 'devel/nss'
            directory.mkdir(parents=True)
            target = directory / 'Makefile'
            target.write_bytes(before)
            argv = self.selected.command('patch') + ('-f', '-E', '-d', str(tree), '-p1', '-F', '0')
            if name == 'wrong':
                with self.assertRaises(subprocess.CalledProcessError):
                    self.runner(argv, input=header + data)
                self.assertEqual(target.read_bytes(), before)
            else:
                output = self.runner(argv, input=header + data)
                self.assertNotIn(b'fuzz', output)
                self.assertNotIn(b'offset', output)
                self.assertEqual(target.read_bytes(), before.replace(old_lines, new_lines))

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

    def test_selected_recipe_does_not_read_external_symlink_files(self):
        outside = self.work / 'outside-input'
        outside.write_bytes(b'external bytes')
        recipes = self.root / 'profiles/selected'
        (recipes / 'distinfo-case').mkdir(parents=True)
        (recipes / 'distinfo-case/Makefile').write_text('PKGNAME=fixture-1\n')
        (recipes / 'distinfo-case/distinfo').symlink_to(outside)
        (recipes / 'patch-case/patches').mkdir(parents=True)
        (recipes / 'patch-case/Makefile').write_text('PKGNAME=fixture-1\n')
        (recipes / 'patch-case/distinfo').write_text(
            'SHA1 (patch-external) = ' + '0' * 40 + '\n')
        (recipes / 'patch-case/patches/patch-external').symlink_to(outside)
        config = self.root / 'pkgsrc/export.conf'
        config.write_text(
            'recipe\tprofiles/selected/distinfo-case\tdevel/distinfo-case\n'
            'recipe\tprofiles/selected/patch-case\tdevel/patch-case\n')
        read_bytes = Path.read_bytes

        def reject_external_read(path):
            if path.resolve() == outside.resolve():
                raise AssertionError('read an external recipe input before link validation')
            return read_bytes(path)

        with mock.patch.object(Path, 'read_bytes', reject_external_read):
            with self.assertRaisesRegex(exporter.ExportError, 'Link leaves the repository'):
                exporter.configuration(self.root)

    def test_selected_recipe_does_not_read_external_patch_symlink(self):
        outside = self.work / 'outside-patch'
        outside.write_bytes(b'external patch bytes')
        recipe = self.root / 'profiles/selected-patch'
        (recipe / 'patches').mkdir(parents=True)
        (recipe / 'Makefile').write_text('PKGNAME=fixture-1\n')
        (recipe / 'distinfo').write_text(
            'SHA1 (patch-external) = ' + '0' * 40 + '\n')
        (recipe / 'patches/patch-external').symlink_to(outside)
        (self.root / 'pkgsrc/export.conf').write_text(
            'recipe\tprofiles/selected-patch\tdevel/selected-patch\n')
        read_bytes = Path.read_bytes

        def reject_external_read(path):
            if path.resolve() == outside.resolve():
                raise AssertionError('read an external patch before link validation')
            return read_bytes(path)

        with mock.patch.object(Path, 'read_bytes', reject_external_read):
            with self.assertRaisesRegex(exporter.ExportError, 'Link leaves the repository'):
                exporter.configuration(self.root)

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
        with self.assertRaisesRegex(exporter.ExportError, 'relative|path'):
            exporter.configuration(self.root)

    def test_export_configuration_rejects_parent_destination_before_writing(self):
        (self.root / 'input').write_bytes(b'outside export')
        (self.root / 'pkgsrc/export.conf').write_text('file\tinput\t../escaped.txt\n')
        escaped = self.work / 'escaped.txt'
        with self.assertRaisesRegex(exporter.ExportError, 'relative|escape|destination'):
            self.fake_export()
        self.assertFalse(escaped.exists())
        self.assertFalse((self.work / 'export').exists())

    def test_export_configuration_rejects_parent_source_and_package_paths(self):
        (self.root / 'input').write_bytes(b'input')
        (self.work / 'input').write_bytes(b'outside input')
        outside_recipe = self.work / 'recipe'
        outside_recipe.mkdir()
        (outside_recipe / 'Makefile').write_text('PKGNAME=outside-1\n')
        (self.root / 'profiles/fixture').mkdir(parents=True)
        (self.root / 'profiles/fixture/Makefile').write_text('PKGNAME=fixture-1\n')
        (self.root / 'patch').write_text('patch fixture\n')
        (self.work / 'patch').write_text('outside patch\n')
        cases = [
            'file\t../input\tCOPIED\n',
            'file\tinput\t../COPIED\n',
            'recipe\t../recipe\tdevel/fixture\n',
            'recipe\tprofiles/fixture\t../outside\n',
            'patch\t../patch\n',
            'git-apply\tpatch\t../manifest\n',
            'recipe-patch\tpatch\tdevel/fixture\t../patch-name\n',
        ]
        for record in cases:
            with self.subTest(record=record):
                (self.root / 'pkgsrc/export.conf').write_text(record)
                with self.assertRaisesRegex(exporter.ExportError,
                        'relative|escape|path|destination|PKGPATH|source|name'):
                    exporter.configuration(self.root)

    def test_export_configuration_rejects_symlinked_source_escape(self):
        outside = self.work / 'outside-source'
        outside.mkdir()
        (outside / 'payload').write_bytes(b'outside')
        (self.root / 'bridge').symlink_to(outside)
        (self.root / 'pkgsrc/export.conf').write_text('file\tbridge/payload\tCOPIED\n')
        with self.assertRaisesRegex(exporter.ExportError, 'source|repository|escape|path'):
            exporter.configuration(self.root)

    def test_overlay_write_refuses_symlinked_destination_parent(self):
        (self.root / 'input').write_bytes(b'overlay')
        (self.root / 'pkgsrc/export.conf').write_text('file\tinput\tlink/escaped.txt\n')
        outside = self.work / 'outside-destination'
        outside.mkdir()
        (self.upstream / 'link').symlink_to(outside)
        with self.assertRaisesRegex(exporter.ExportError, 'destination|symlink|escape|path'):
            self.fake_export()
        self.assertFalse((outside / 'escaped.txt').exists())

    def test_new_category_copy_rejects_external_symlinks_and_symlinked_category(self):
        outside = self.work / 'outside-category'
        outside.mkdir()
        (outside / 'payload').write_bytes(b'external category data')
        category = self.root / 'pkgsrc/newcategory'
        category.mkdir()
        (category / 'README').symlink_to(outside / 'payload')
        with self.assertRaisesRegex(exporter.ExportError, 'symlink|repository|escape|outside'):
            self.fake_export()
        self.assertFalse((self.work / 'export').exists())

        (category / 'README').unlink()
        category.rmdir()
        category.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(exporter.ExportError, 'symlink|category|repository|escape'):
            self.fake_export()
        self.assertFalse((self.work / 'export').exists())

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
        done = subprocess.run(['/bin/sh', 'prepare-pkgsrc.sh', str(existing),
            '--sdk-source', sdk_root, '--host-prefix', '/unused-prefix'],
            cwd=HERE.parent, env={**os.environ, 'PY': sys.executable},
            capture_output=True, text=True)
        self.assertEqual(done.returncode, 2)
        self.assertIn('Destination already exists.', done.stderr)

    def test_cli_exports_with_host_prefix_without_receipts(self):
        from emberbsd_sdk import native_toolset
        selected = types.SimpleNamespace(command=self.selected.command,
            tool=lambda role: sys.executable if role == 'python' else self.selected.command(role)[0],
            path=str(self.work / 'host-pkg-g16/bin'))
        def capture(argv, **kwargs):
            self.assertEqual(kwargs.pop('env')['PATH'], selected.path)
            for name in ('stdout', 'stderr', 'check'): kwargs.pop(name)
            if argv[-1:] == ['--help']:
                return types.SimpleNamespace(stdout=self.patch_help)
            return types.SimpleNamespace(stdout=self.runner(argv, **kwargs))
        destination = self.work / 'direct-export'
        sys.path.insert(0, str(HERE.parents[1] / 'pkgsrc/lang/llvm/files'))
        with mock.patch.dict(os.environ, FAKE_ARCHIVE=str(self.upstream), FAKE_MATCH='1'), \
             mock.patch.object(exporter, '__file__', str(self.root / 'scripts/prepare-pkgsrc.py')), \
             mock.patch.object(native_toolset, 'load_host_prefix', return_value=selected) as load, \
             mock.patch.object(exporter.subprocess, 'run', side_effect=capture):
            self.assertEqual(exporter.main([str(destination), '--sdk-source', sdk_root,
                             '--host-prefix', str(self.work / 'host-pkg-g16')]), 0)
        self.assertEqual((destination / 'plain').read_bytes(), b'one\ntwo\nthree\n')
        self.assertEqual(load.call_args.args, (str(self.work / 'host-pkg-g16'),))
        self.assertEqual(load.call_args.kwargs, {'required_roles': ('git', 'patch')})
        self.assertFalse(list(self.work.glob('.pkgsrc-export-*')))

    def test_cli_exports_source_without_sdk_or_compiler(self):
        destination = self.work / 'acquisition-export'
        commands = {role: self.selected.command(role)[0] for role in ('git', 'patch')}
        def source_child(argv, **kwargs):
            self.assertIn(argv[0], commands.values())
            for name in ('env', 'stdout', 'stderr', 'check'): kwargs.pop(name)
            if argv[-1:] == ['--help']:
                return types.SimpleNamespace(stdout=self.patch_help)
            return types.SimpleNamespace(stdout=self.runner(argv, **kwargs))
        with mock.patch.dict(os.environ, FAKE_ARCHIVE=str(self.upstream), FAKE_MATCH='1'), \
             mock.patch.dict(sys.modules, {'emberbsd_sdk.native_toolset': None}), \
             mock.patch.object(exporter, '__file__', str(self.root / 'scripts/prepare-pkgsrc.py')), \
             mock.patch.object(exporter.subprocess, 'run', side_effect=source_child):
            self.assertEqual(exporter.main([str(destination), '--git', commands['git'],
                                          '--patch', commands['patch']]), 0)
        self.assertEqual((destination / 'plain').read_bytes(), b'one\ntwo\nthree\n')
        self.assertFalse(list(self.work.glob('.pkgsrc-export-*')))

    def test_three_standalone_entries_refuse_unrelated_selectors(self):
        root = HERE.parents[1]
        entries = [[sys.executable, '-B', str(root / 'scripts/prepare-pkgsrc.py')],
                   ['/bin/sh', str(root / 'scripts/prepare-pkgsrc.sh')],
                   [sys.executable, '-B', str(root / 'probes/lxqt/prepare-pkgsrc.py')]]
        for number, entry in enumerate(entries):
            destination = self.work / ('refused-' + str(number))
            argv = entry + [str(destination), '--sdk-source', '/not-opened',
                            '--host-prefix', '/not-opened', '--descriptor', '/not-opened']
            done = subprocess.run(argv, env={**os.environ, 'PY': sys.executable},
                                  capture_output=True, text=True)
            self.assertEqual(done.returncode, 2)
            self.assertIn('unrecognized arguments: --descriptor', done.stderr)
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
        patch = (b'--- a/plain\n+++ b/plain\n@@ -1,3 +0,0 @@\n-one\n-two\n-three\n'
                 b'--- a/keep\n+++ b/keep\n@@ -1 +1 @@\n-before\n+after\n')
        (self.upstream / 'keep').write_bytes(b'before\n')
        (self.root / 'remove.patch').write_bytes(patch)
        (self.root / 'pkgsrc/export.conf').write_text('patch\tremove.patch\n')
        self.fake_export()
        self.assertFalse((self.work / 'export/plain').exists())
        self.assertFalse((self.work / 'export/plain.orig').exists())
        self.assertEqual((self.work / 'export/keep').read_bytes(), b'after\n')
        self.assertFalse((self.work / 'export/keep.orig').exists())
        self.assertIn(['-f', '-E', '-d', str(self.work / 'export'), '-p1', '-F', '0',
                       '-V', 'none', *exporter.patch_safety_options(self.selected, self.runner)],
                      [argv[1:] for argv, options in self.commands if argv[0] == self.selected.command('patch')[0]])
        control = self.work / 'without-E'
        control.mkdir()
        (control / 'plain').write_bytes(b'one\ntwo\nthree\n')
        (control / 'keep').write_bytes(b'before\n')
        self.runner([self.selected.command('patch')[0], '-f', '-d', str(control), '-p1', '-F', '0'], input=patch)
        self.assertEqual((control / 'plain').read_bytes(), b'')

    def test_nbpatch_uses_supported_no_backup_mode(self):
        if Path(self.selected.command('patch')[0]).name != 'nbpatch':
            self.skipTest('Set EXPORT_TEST_PATCH to the SDK nbpatch executable.')
        patch = (b'--- a/plain\n+++ b/plain\n@@ -1,3 +1,3 @@\n one\n-two\n+changed\n three\n'
                 b'--- /dev/null\n+++ b/added\n@@ -0,0 +1 @@\n+new file\n')
        (self.root / 'change.patch').write_bytes(patch)
        (self.root / 'pkgsrc/export.conf').write_text('patch\tchange.patch\n')

        self.fake_export('nbpatch-export')

        self.assertEqual((self.work / 'nbpatch-export/plain').read_bytes(), b'one\nchanged\nthree\n')
        self.assertEqual((self.work / 'nbpatch-export/added').read_bytes(), b'new file\n')
        self.assertFalse((self.work / 'nbpatch-export/plain.orig').exists())
        self.assertFalse((self.work / 'nbpatch-export/added.orig').exists())
        command = next(argv for argv, options in self.commands
                       if argv[0] == self.selected.command('patch')[0] and argv[1:2] == ['-f'])
        self.assertEqual(command[1:], ['-f', '-E', '-d', str(self.work / 'nbpatch-export'),
                                       '-p1', '-F', '0', '-V', 'none',
                                       *exporter.patch_safety_options(self.selected, self.runner)])
        self.assertNotIn('--posix', command)

    def test_export_patch_disables_platform_default_backups(self):
        owner = HERE.parents[1]
        relative = Path('lang/gcc16/Makefile')
        (self.upstream / relative).parent.mkdir(parents=True)
        shutil.copyfile(owner / 'upstream/pkgsrc' / relative,
                        self.upstream / relative)
        relative_patch = Path('lang/gcc16/patches/patch-isl_configure')
        (self.upstream / relative_patch).parent.mkdir(parents=True)
        shutil.copyfile(owner / 'upstream/pkgsrc' / relative_patch,
                        self.upstream / relative_patch)
        preexisting_backup = self.upstream / 'lang/gcc16/Makefile.~1~'
        preexisting_backup.write_text('legitimate upstream file\n')
        patch = owner / 'profiles/development-toolchain/patches/strict-tests.patch'
        (self.root / 'strict-tests.patch').write_bytes(patch.read_bytes())
        (self.root / 'pkgsrc/export.conf').write_text('patch\tstrict-tests.patch\n')

        self.fake_export()

        self.assertFalse((self.work / 'export/lang/gcc16/Makefile.orig').exists())
        self.assertFalse((self.work / 'export/lang/gcc16/patches/patch-isl_configure.orig').exists())
        self.assertEqual((self.work / 'export/lang/gcc16/Makefile.~1~').read_text(),
                         'legitimate upstream file\n')
        self.assertEqual(exporter.numbered_backup_paths(self.work / 'export'),
                         {Path('lang/gcc16/Makefile.~1~')})
        self.assertIn(['-f', '-E', '-d', str(self.work / 'export'), '-p1', '-F', '0',
                       '-V', 'none', *exporter.patch_safety_options(self.selected, self.runner)],
                      [argv[1:] for argv, options in self.commands if argv[0] == self.selected.command('patch')[0]])

    def test_export_rejects_patch_created_numbered_backup(self):
        (self.root / 'change.patch').write_bytes(b'fixture patch')
        (self.root / 'pkgsrc/export.conf').write_text('patch\tchange.patch\n')

        def creates_backup(argv, **kwargs):
            if argv[0] == self.selected.command('patch')[0] and argv[1:2] == ['-f']:
                (self.work / 'export/plain.~1~').write_text('created by patch\n')
                return b''
            return self.runner(argv, **kwargs)

        with self.assertRaisesRegex(exporter.ExportError,
                                    'Patch application created numbered backup artifacts'):
            self.fake_export(runner=creates_backup)

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
