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
