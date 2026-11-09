#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Check owned cross-libtool context reuse and interrupted attempts."""
import importlib.util
import os
from pathlib import Path
import subprocess
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
                    self.assertEqual(argv[-2], 'CFLAGS=-O2')
                    self.assertEqual(argv[-3], 'PREFIX=' + str(root))
                    self.assertEqual(cookie.read_text(), 'native dependencies ready')
            producer.build_package(make, '/selected/native', '/selected/native/pkgdb', root,
                                   '/selected/native/sbin/pkg_add',
                                   SimpleNamespace(run_logged=run), {'PATH': '/selected/native/bin'})
            self.assertEqual([call[0][-1] for call in calls], ['depends', 'package'])
            self.assertEqual(calls[0][0][:-3], make)
            self.assertEqual(calls[1][0][:-3], make)
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

    def test_selected_makeconf_names_the_host_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            prefix = root / 'host'
            prefix.mkdir()
            database = root / 'host-pkgdb'
            self._install_package(database, prefix)
            sysroot = root / 'sysroot'
            (sysroot / 'usr/pkg/pkgdb').mkdir(parents=True)
            calls = []
            def capture(argv, *, env):
                calls.append((argv, env))
                return SimpleNamespace(stdout=(str(prefix) + '\n' + str(database) + '\n').encode())
            env = {'PATH': str(prefix / 'bin'), 'PKG_DBDIR': str(sysroot / 'usr/pkg/pkgdb'),
                   'HOST_PKG_DBDIR': str(sysroot / 'usr/pkg/pkgdb')}
            selected = producer.resolve_native_database(
                pkg_admin=str(prefix / 'sbin/pkg_admin'), process=SimpleNamespace(capture=capture),
                env=env, prefix=str(prefix), sysroot=str(sysroot),
                native_makeconf=str(root / 'native.mk'), make=str(prefix / 'bin/bmake'),
                pkgsrc=str(root / 'pkgsrc'))
            self.assertEqual(selected, str(database))
            self.assertEqual(calls[0][0], [
                str(prefix / 'bin/bmake'), '-C', str(root / 'pkgsrc/pkgtools/pkg_install'),
                'USE_CROSS_COMPILE=no', 'MAKECONF=' + str(root / 'native.mk'),
                'show-vars', 'VARNAMES=PREFIX PKG_DBDIR'])
            self.assertNotIn('PKG_DBDIR', calls[0][1])
            self.assertNotIn('HOST_PKG_DBDIR', calls[0][1])
            self.assertNotIn('config-var', calls[0][0])
            self.assertEqual(calls[0][1]['PATH'], os.pathsep.join((
                str(prefix / 'bin'), str(prefix / 'sbin'), '/usr/bin', '/bin', '/usr/sbin', '/sbin')))

    def test_show_vars_environment_runs_system_sed_and_echo(self):
        bmake = '/usr/bin/bmake'
        if not (os.path.isfile(bmake) and os.access(bmake, os.X_OK)):
            self.skipTest('no /usr/bin/bmake binary is installed')
        with open(bmake, 'rb') as stream:
            if stream.read(4) != b'\x7fELF':
                self.skipTest('/usr/bin/bmake is not an ELF bmake binary')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            prefix = root / 'host'
            (prefix / 'bin').mkdir(parents=True)
            (prefix / 'sbin').mkdir()
            gsed = prefix / 'bin' / 'gsed'
            gsed.write_text('#!/bin/sh\nprintf gsed-not-sed\\n')
            gsed.chmod(0o755)
            stub = root / 'pkgtools' / 'pkg_install'
            stub.mkdir(parents=True)
            (stub / 'Makefile').write_text(
                'ECHO_RESULT!= env echo ember-echo-ok\n'
                'SED_RESULT!= env echo ember-sed-ok | env sed s/ember-//\n')
            ready = producer.show_vars_environment(
                {'PATH': '/blocked', 'PKG_DBDIR': '/wrong-db', 'HOST_PKG_DBDIR': '/wrong-host',
                 'MAKECONF': '/dev/null', 'LC_ALL': 'C'}, str(prefix))
            self.assertNotIn('PKG_DBDIR', ready)
            self.assertNotIn('HOST_PKG_DBDIR', ready)
            self.assertNotIn('/blocked', ready['PATH'])
            self.assertEqual(ready['PATH'], os.pathsep.join((
                str(prefix / 'bin'), str(prefix / 'sbin'), '/usr/bin', '/bin', '/usr/sbin', '/sbin')))
            self.assertEqual(producer.native_build_path(str(prefix)), os.pathsep.join((
                str(prefix / 'bin'), str(prefix / 'gnu/bin'), str(prefix / 'sbin'),
                '/usr/bin', '/bin', '/usr/sbin', '/sbin')))
            # This bmake may predate the show-vars target. -V evaluates the same
            # makefile commands under the query environment.
            probe = subprocess.run([bmake, '-r', '-C', str(stub), 'show-vars', 'VARNAMES=ECHO_RESULT SED_RESULT'],
                                   env=ready, capture_output=True, text=True)
            if probe.returncode == 0:
                values = probe.stdout.splitlines()
            else:
                self.assertIn('show-vars', probe.stderr)
                probe = subprocess.run([bmake, '-r', '-C', str(stub), '-V', 'ECHO_RESULT', '-V', 'SED_RESULT'],
                                       env=ready, capture_output=True, text=True)
                self.assertEqual(probe.returncode, 0, probe.stderr)
                values = probe.stdout.splitlines()
            self.assertEqual(values, ['ember-echo-ok', 'sed-ok'])
            blocked = dict(ready, PATH=os.pathsep.join((str(prefix / 'bin'), str(prefix / 'sbin'))))
            missed = subprocess.run([bmake, '-r', '-C', str(stub), '-V', 'ECHO_RESULT', '-V', 'SED_RESULT'],
                                    env=blocked, capture_output=True, text=True)
            self.assertNotIn('sed-ok', missed.stdout)

    def test_selected_makeconf_refuses_target_database_and_wrong_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            prefix = root / 'host'
            prefix.mkdir()
            sysroot = root / 'sysroot'
            target = sysroot / 'usr/pkg/pkgdb'
            self._install_package(target, prefix)
            other = root / 'other-pkgdb'
            self._install_package(other, root / 'other-prefix')
            foreign_prefix = root / 'foreign-host'
            foreign_prefix.mkdir()
            def answer(prefix_text, database):
                def capture(argv, *, env):
                    return SimpleNamespace(stdout=(prefix_text + '\n' + str(database) + '\n').encode())
                return SimpleNamespace(capture=capture)
            kwargs = dict(pkg_admin=str(prefix / 'sbin/pkg_admin'), env={'PATH': '/bin'},
                          prefix=str(prefix), sysroot=str(sysroot),
                          native_makeconf=str(root / 'native.mk'), make=str(prefix / 'bin/bmake'),
                          pkgsrc=str(root / 'pkgsrc'))
            with self.assertRaisesRegex(ValueError, 'target sysroot'):
                producer.resolve_native_database(process=answer(str(prefix), target), **kwargs)
            with self.assertRaisesRegex(ValueError, 'another prefix'):
                producer.resolve_native_database(process=answer(str(prefix), other), **kwargs)
            mixed = root / 'mixed-pkgdb'
            self._install_package(mixed, prefix)
            (mixed / 'foreign-1.0').mkdir()
            (mixed / 'foreign-1.0' / '+CONTENTS').write_text(
                '@cwd ' + str(prefix) + '\n@cwd ' + str(root / 'other-prefix') + '\n')
            with self.assertRaisesRegex(ValueError, 'another prefix'):
                producer.resolve_native_database(process=answer(str(prefix), mixed), **kwargs)
            spaced = root / 'spaced-pkgdb'
            self._install_package(spaced, prefix)
            (spaced / 'example-1.0' / '+CONTENTS').write_text('@cwd ' + str(prefix) + ' \n')
            with self.assertRaisesRegex(ValueError, 'another prefix'):
                producer.resolve_native_database(process=answer(str(prefix), spaced), **kwargs)
            with self.assertRaisesRegex(ValueError, 'differs from the host prefix'):
                producer.resolve_native_database(process=answer(str(foreign_prefix), other), **kwargs)
            link = root / 'linked-pkgdb'
            link.symlink_to(other)
            with self.assertRaisesRegex(ValueError, 'invalid package database'):
                producer.resolve_native_database(process=answer(str(prefix), link), **kwargs)
            self.assertFalse((root / 'context').exists())

    def test_omitted_makeconf_keeps_compiled_pkg_admin_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp).resolve() / 'pkgdb'
            database.mkdir()
            calls = []
            def capture(argv, *, env):
                calls.append(argv)
                return SimpleNamespace(stdout=(str(database) + '\n').encode())
            selected = producer.resolve_native_database(
                pkg_admin='/selected/sbin/pkg_admin', process=SimpleNamespace(capture=capture),
                env={'PATH': '/selected/bin'}, prefix='/selected', sysroot='/sysroot')
            self.assertEqual(selected, str(database))
            self.assertEqual(calls, [['/selected/sbin/pkg_admin', 'config-var', 'PKG_DBDIR']])

    def test_wrong_prefix_inserted_before_the_lock_is_not_built(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            prefix = root / 'host'
            prefix.mkdir()
            database = root / 'host-pkgdb'
            self._install_package(database, prefix)
            sysroot = root / 'sysroot'
            (sysroot / 'usr/pkg/pkgdb').mkdir(parents=True)
            def capture(argv, *, env):
                return SimpleNamespace(stdout=(str(prefix) + '\n' + str(database) + '\n').encode())
            selected = producer.resolve_native_database(
                pkg_admin=str(prefix / 'sbin/pkg_admin'), process=SimpleNamespace(capture=capture),
                env={'PATH': str(prefix / 'bin')}, prefix=str(prefix), sysroot=str(sysroot),
                native_makeconf=str(root / 'native.mk'), make=str(prefix / 'bin/bmake'),
                pkgsrc=str(root / 'pkgsrc'))
            self.assertEqual(selected, str(database))
            foreign = database / 'foreign-9.9'
            foreign.mkdir()
            (foreign / '+CONTENTS').write_text('@cwd ' + str(root / 'other-prefix') + '\n')
            calls = []
            def run_logged(argv, log, *, env):
                calls.append(argv[-1])
            sys.path.insert(0, os.path.join(os.environ['EMBERBSD_SDK_SOURCE'], 'src'))
            from emberbsd_sdk.process import ContextLocks
            # Injection is before the lock. The default lock directory is the
            # parent of the host prefix; the subjects are that prefix and the
            # same database path resolve returned.
            with ContextLocks([str(prefix), selected], str(prefix.parent)):
                with self.assertRaisesRegex(ValueError, 'another prefix'):
                    producer.build_selected_package(
                        ['/selected/bmake'], str(prefix), selected, str(sysroot), root / 'context',
                        str(prefix / 'sbin/pkg_add'), SimpleNamespace(run_logged=run_logged),
                        {'PATH': str(prefix / 'bin')}, prove_contents=True)
            self.assertEqual(calls, [])
            self.assertEqual(selected, str(database))

    def test_repeated_identical_cwd_names_the_same_host_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            prefix = root / 'host'
            prefix.mkdir()
            database = root / 'host-pkgdb'
            sysroot = root / 'sysroot'
            sysroot.mkdir()
            self._install_package(database, prefix)
            (database / 'example-1.0' / '+CONTENTS').write_text(
                '@name example-1.0\n@cwd ' + str(prefix) + '\n@cwd ' + str(prefix) + '\n')
            self.assertEqual(producer.selected_host_database(str(database), str(prefix), str(sysroot)),
                             str(database))

    def _install_package(self, database, prefix):
        database.mkdir(parents=True, exist_ok=True)
        package = database / 'example-1.0'
        package.mkdir()
        (package / '+CONTENTS').write_text('@name example-1.0\n@cwd ' + str(prefix) + '\n')

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
                (context / 'target-tools/bin').mkdir(parents=True)
            alias = producer.activate_context(tools, root, one)
            self.assertEqual(alias.read_text(), one.name)
            target_alias = one / 'target-tools/bin/target-libtool'
            self.assertTrue(target_alias.is_symlink())
            self.assertEqual(target_alias.resolve(), (one / 'bin/target-libtool').resolve())
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
