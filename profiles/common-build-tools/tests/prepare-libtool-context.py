#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Check owned cross-libtool context reuse and interrupted attempts."""
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

cross = Path(__file__).resolve().parents[1] / 'cross'
sys.path.insert(0, str(cross))
spec = importlib.util.spec_from_file_location('producer', cross / 'prepare-libtool.py')
producer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(producer)

class ContextTest(unittest.TestCase):
    def test_dependencies_use_native_prefix_before_provider_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cookie = root / 'depends-cookie'
            calls = []
            make = ['/selected/bmake', 'MAKECONF=/selected/cross.conf',
                    'USE_CROSS_COMPILE=no', 'TARGET_MACHINE_ARCH=aarch64']
            def run(argv, log, *, env):
                calls.append((argv, log, env))
                if argv[-1] == 'depends':
                    self.assertEqual(argv[-3], 'PREFIX=/selected/native')
                    self.assertEqual(argv[-2], 'PKG_ADD=/selected/native/sbin/pkg_add -K /selected/native/pkgdb -U')
                    cookie.write_text('native dependencies ready')
                else:
                    self.assertEqual(argv[-1], 'package')
                    self.assertEqual(argv[-2], 'PREFIX=' + str(root))
                    self.assertEqual(cookie.read_text(), 'native dependencies ready')
            producer.build_package(make, '/selected/native', '/selected/native/pkgdb', root,
                                   '/selected/native/sbin/pkg_add',
                                   SimpleNamespace(run_logged=run), {'PATH': '/selected/native/bin'})
            self.assertEqual([call[0][-1] for call in calls], ['depends', 'package'])
            self.assertEqual(calls[0][0][:-3], make)
            self.assertEqual(calls[1][0][:-2], make)
            def fail(*args, **kwargs):
                raise ValueError('dependency failure')
            with self.assertRaisesRegex(ValueError, 'dependency failure'):
                producer.build_package(make, '/selected/native', '/selected/native/pkgdb', root,
                                       '/selected/native/sbin/pkg_add',
                                       SimpleNamespace(run_logged=fail), {})

    def test_package_database_comes_from_native_pkg_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            database = root / 'pkgdb'
            database.mkdir()
            calls = []
            def reply(value):
                def capture(argv, *, env):
                    calls.append((argv, env))
                    return SimpleNamespace(stdout=value)
                return SimpleNamespace(capture=capture)
            env = {'PATH': '/selected/native/bin'}
            self.assertEqual(producer.native_package_database(
                '/selected/native/sbin/pkg_admin', reply(str(database).encode() + b'\n'), env),
                str(database))
            self.assertEqual(calls[0], (['/selected/native/sbin/pkg_admin', 'config-var', 'PKG_DBDIR'], env))
            (root / 'link').symlink_to(database)
            (root / 'parent').symlink_to(root)
            for value in (b'pkgdb\n', str(root / 'missing').encode(), str(root / 'link').encode(),
                          str(root / 'link').encode() + b'/', str(root / 'link').encode() + b'/.',
                          str(root / 'parent/pkgdb').encode(), b'', str(database).encode() + b' x'):
                with self.assertRaisesRegex(ValueError, 'invalid package database'):
                    producer.native_package_database('/selected/native/sbin/pkg_admin', reply(value), env)
            self.assertEqual(producer.package_database_conf('/selected/native/pkgdb'),
                             ['HOST_PKG_DBDIR=/selected/native/pkgdb', 'PKG_DBDIR=/selected/native/pkgdb'])

    def test_clang_runtime_uses_foundation_only_for_explicit_stage(self):
        paths = SimpleNamespace(canonical_existing=lambda p: p)
        stage = SimpleNamespace(FULL_COMPONENTS=('runtime',), validate_stage=Mock(return_value={'stage': 'ok'}))
        ready = SimpleNamespace(load_clang_runtime=Mock(return_value={'base': {'files': {'lib/libc.so': 'old'}}}))
        result = producer.clang_runtime('/final', 'aarch64', '/stage', '/foundation', paths, stage, ready)
        self.assertEqual(result, {'stage': 'ok'})
        self.assertEqual(stage.validate_stage.call_args.kwargs['base'], '/foundation')
        producer.clang_runtime('/final', 'aarch64', '/stage', None, paths, stage, ready)
        self.assertEqual(stage.validate_stage.call_args.kwargs['base'], '/final')
        result = producer.clang_runtime('/final', 'aarch64', None, None, paths, stage, ready)
        self.assertEqual(result['base']['files']['lib/libc.so'], 'old')
        ready.load_clang_runtime.assert_called_once_with('/final', target='aarch64')
        ready.load_clang_runtime.side_effect = ValueError('damaged runtime')
        with self.assertRaisesRegex(ValueError, 'damaged runtime'):
            producer.clang_runtime('/final', 'aarch64', None, None, paths, stage, ready)

    def test_actual_sysroot_inputs_change_with_library_or_header(self):
        sys.path.insert(0, os.path.join(os.environ['EMBERBSD_SDK_SOURCE'], 'src'))
        from emberbsd_sdk import inventory
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            for name in ('lib', 'usr/lib', 'usr/include'):
                (root / name).mkdir(parents=True)
            libc = root / 'lib/libc.so.12'
            libc.write_text('first')
            (root / 'usr/lib/libc.so').symlink_to('../../lib/libc.so.12')
            header = root / 'usr/include/stdio.h'
            header.write_text('first')
            before = producer.sysroot_inputs(str(root), inventory)
            libc.write_text('second')
            self.assertNotEqual(before, producer.sysroot_inputs(str(root), inventory))
            before = producer.sysroot_inputs(str(root), inventory)
            header.write_text('second')
            self.assertNotEqual(before, producer.sysroot_inputs(str(root), inventory))

    def test_stage_rename_keeps_the_context_key_and_reaches_the_new_stage(self):
        sys.path.insert(0, os.path.join(os.environ['EMBERBSD_SDK_SOURCE'], 'src'))
        from emberbsd_sdk import inventory, paths
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp).resolve()
            stage = tmp / 'stages/s8/dest'
            for name in ('lib', 'usr/lib', 'usr/include'):
                (stage / name).mkdir(parents=True)
            (stage / 'lib/libc.so.12').write_text('libc')
            (stage / 'usr/include/stdio.h').write_text('stdio')
            recipe = tmp / 'pkgsrc'
            for directory in ('cross/cross-libtool-base', 'devel/libtool-base', 'devel/libtool'):
                (recipe / directory).mkdir(parents=True)
                (recipe / directory / 'Makefile').write_text('recipe')
            output = tmp / 'tools/gettext-libtool'
            output.parent.mkdir()

            def key(sysroot):
                # The parts of the producer key that read the stage: the
                # spelling given to the tools, and the real stage contents.
                return producer.context_name({'sysroot': sysroot,
                    'sysroot_inputs': producer.sysroot_inputs(os.path.realpath(sysroot), inventory),
                    'recipe': producer.recipe_digest(recipe)})

            def old(selected):
                return paths.canonical_existing(selected)

            def new(selected):
                return producer.bind_sysroot(output, paths.canonical_existing(selected))

            old_key, new_key = key(old(stage)), key(new(stage))
            renamed = tmp / 'stages/s8b/dest'
            renamed.parent.mkdir()
            stage.rename(renamed)
            self.assertNotEqual(key(old(renamed)), old_key)
            alias = new(renamed)
            self.assertEqual(key(alias), new_key)
            self.assertEqual(alias, str(output / 'sysroot'))
            self.assertEqual(os.readlink(alias), str(renamed))
            self.assertEqual((Path(alias) / 'usr/include/stdio.h').read_text(), 'stdio')
            # Other headers, libraries or recipe still select another context.
            (renamed / 'usr/include/stdio.h').write_text('other stdio')
            self.assertNotEqual(key(new(renamed)), new_key)
            (renamed / 'usr/include/stdio.h').write_text('stdio')
            self.assertEqual(key(new(renamed)), new_key)
            (recipe / 'devel/libtool/Makefile').write_text('changed recipe')
            self.assertNotEqual(key(new(renamed)), new_key)
            # Only an alias link is ever replaced.
            (output / 'sysroot').unlink()
            (output / 'sysroot').mkdir()
            with self.assertRaisesRegex(ValueError, 'incompatible cross-libtool sysroot alias'):
                new(renamed)

    def test_recipe_identity_tracks_patch_inventory_but_not_unrelated_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for directory in ('cross/cross-libtool-base', 'devel/libtool-base', 'devel/libtool'):
                item = root / directory
                item.mkdir(parents=True)
                (item / 'Makefile').write_text('recipe')
            patchdir = root / 'devel/libtool/patches'
            patchdir.mkdir()
            (patchdir / 'patch-one').write_text('one')
            before = producer.recipe_digest(root)
            (root / 'devel/libtool/DESCR').write_text('description')
            self.assertEqual(producer.recipe_digest(root), before)
            (patchdir / 'patch-two').write_text('two')
            self.assertNotEqual(producer.recipe_digest(root), before)

    def test_partial_retry_uses_one_owned_context_and_rejects_other_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'libtool'
            identity = {'target': 'aarch64', 'recipe': 'one'}
            context, reused = producer.claim_context(root, identity)
            self.assertFalse(reused)
            (context / 'build.log').write_text('old')
            (context / 'depends.log').write_text('old')
            same, reused = producer.claim_context(root, identity)
            self.assertFalse(reused)
            self.assertEqual(same, context)
            self.assertFalse((same / 'build.log').exists())
            (same / 'bin').mkdir()
            (same / 'bin/target-libtool').touch()
            self.assertEqual(producer.claim_context(root, identity), (same, True))
            other, reused = producer.claim_context(root, {'target': 'amd64', 'recipe': 'one'})
            self.assertNotEqual(other, same)
            self.assertFalse(reused)

    def test_switch_context_keeps_stable_alias_and_does_not_replace_foreign(self):
        with tempfile.TemporaryDirectory() as tmp:
            tools = Path(tmp) / 'tools'
            (tools / 'bin').mkdir(parents=True)
            root = tools / 'gettext-libtool'
            one, _ = producer.claim_context(root, {'recipe': 'one'})
            two, _ = producer.claim_context(root, {'recipe': 'two'})
            for context in (one, two):
                (context / 'bin').mkdir()
                (context / 'bin/target-libtool').write_text(context.name)
            alias = producer.activate_context(tools, root, one)
            self.assertEqual(alias.read_text(), one.name)
            producer.activate_context(tools, root, two)
            self.assertEqual(alias.read_text(), two.name)
            alias.unlink()
            alias.write_text('foreign')
            with self.assertRaisesRegex(ValueError, 'incompatible'):
                producer.activate_context(tools, root, one)
            self.assertEqual(alias.read_text(), 'foreign')
            self.assertEqual((root / 'current').resolve(), two.resolve())

    def test_partial_context_with_unknown_files_is_not_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'libtool'
            identity = {'target': 'aarch64'}
            context, _ = producer.claim_context(root, identity)
            (context / 'foreign').write_text('keep')
            with self.assertRaisesRegex(ValueError, 'incompatible files'):
                producer.claim_context(root, identity)
            self.assertEqual((context / 'foreign').read_text(), 'keep')

    def test_incomplete_active_context_is_not_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'libtool'
            identity = {'target': 'aarch64'}
            context, _ = producer.claim_context(root, identity)
            (context / 'build.log').write_text('preserve')
            (root / 'current').symlink_to(context.name)
            with self.assertRaisesRegex(ValueError, 'active'):
                producer.claim_context(root, identity)
            self.assertEqual((context / 'build.log').read_text(), 'preserve')

    def test_foreign_context_is_not_changed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'libtool'
            identity = {'target': 'aarch64'}
            context = root / producer.context_name(identity)
            context.mkdir(parents=True)
            (context / 'foreign').write_text('keep')
            with self.assertRaisesRegex(ValueError, 'incompatible'):
                producer.claim_context(root, identity)
            self.assertEqual((context / 'foreign').read_text(), 'keep')

if __name__ == '__main__':
    unittest.main()
