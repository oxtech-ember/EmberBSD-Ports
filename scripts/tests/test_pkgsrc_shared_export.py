# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""One shared pkgsrc export serves every source owner of a run."""

import hashlib
import importlib.util
import inspect
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SDK = Path(os.environ['EMBERBSD_SDK_SOURCE'])
WORK = Path(os.environ['EMBERBSD_TEST_WORK'])
sys.path.insert(0, str(ROOT / 'pkgsrc/lang/llvm/files'))
sys.path.insert(0, str(SDK / 'src'))
OWNERS = ('libevent', 'byacc', 'texinfo', 'rcs', 'diffutils', 'grep', 'ekermit', 'nvi',
          'tdb', 'ppp', 'libpcap', 'tcp_wrappers')
GIT_OWNERS = ('7zip', 'brotli', 'byacc', 'diffutils', 'ekermit', 'gettext', 'grep', 'iscsi', 'libevent',
              'libpcap', 'libxml2', 'ntp', 'nvi', 'ppp', 'protobuf', 'rcs', 'tcp_wrappers', 'tcpdump',
              'tdb', 'texinfo', 'top')


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


identity = load(ROOT / 'scripts/pkgsrc-source-identity.py', 'identity')


def fixture(root):
    for name in ('scripts', 'pkgsrc/cat/pkg', 'pkgsrc/lang/llvm/files', 'upstream/pkgsrc'):
        (root / name).mkdir(parents=True)
    shutil.copy(ROOT / 'scripts/prepare-pkgsrc.py', root / 'scripts')
    shutil.copy(ROOT / 'scripts/pkgsrc-export-stage.py', root / 'scripts')
    shutil.copy(ROOT / 'pkgsrc/lang/llvm/files/sdk_source.py', root / 'pkgsrc/lang/llvm/files')
    (root / 'pkgsrc/lang/llvm/Makefile').write_text('DISTNAME=llvm\n')
    (root / 'pkgsrc/export.conf').write_text('')
    (root / 'pkgsrc/cat/pkg/Makefile').write_text('DISTNAME=example\n')
    tool = root / 'tool/patch'
    tool.parent.mkdir()
    tool.write_text('#!/bin/sh\n')
    tool.chmod(0o755)
    return tool


class SharedExportTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=WORK)
        self.root = Path(self.temp.name) / 'ports'
        self.tool = fixture(self.root)
        self.pins = {'upstream': b'1' * 40, 'ports': b'a' * 40}

        def git(argv, *, env):
            if 'ls-files' in argv:
                return b'160000 ' + self.pins['upstream'] + b' 0\tupstream/pkgsrc\n'
            if Path(argv[2]) == self.root:
                return self.pins['ports'] + b'\n'
            return self.pins['upstream'] + b'\n'
        self.git = patch.object(identity.subprocess, 'check_output', side_effect=git)
        self.git.start()
        self.exports = []

        def export(command, **kwargs):
            # Stand in for prepare-pkgsrc.py: a tree plus its revision file.
            self.exports.append(command)
            tree = Path(command[3])
            (tree / 'cat/pkg').mkdir(parents=True)
            (tree / 'net/libfetch/files').mkdir(parents=True)
            (tree / 'EMBERBSD-PKGSRC-REVISION').write_text(self.pins['upstream'].decode() + '\n')
        self.run = patch.object(identity.subprocess, 'run', side_effect=export)
        self.run.start()

    def tearDown(self):
        self.run.stop()
        self.git.stop()
        self.temp.cleanup()

    def select(self, directory):
        return identity.shared_export(directory, self.root, sys.executable, SDK, str(self.tool))

    def test_consumer_patch_is_distinct_from_export_producer(self):
        from types import SimpleNamespace
        from emberbsd_sdk import sourceprep
        producer = self.tool
        consumer = os.environ.get('EMBERBSD_TEST_GPATCH')
        if not consumer:
            self.skipTest('select the native GNU patch for the source operation')
        directory = Path(self.temp.name) / 'export'
        identity.create_shared_export(directory, self.root, sys.executable, SDK, str(producer))
        owner = load(ROOT / 'scripts/source-inputs/libevent/source.py', 'separate_patch_owner')
        selected = SimpleNamespace(pkgsrc_export=str(directory), git=sys.executable,
                                   patch=consumer, export_patch=str(producer))
        receipt = directory / 'pkgsrc-export.json'
        tree = directory / 'pkgsrc'
        stamps = [(path.stat().st_mtime_ns, path.stat().st_ino) for path in (receipt, tree)]
        with patch.object(owner, 'PORTS', self.root), patch.object(owner, 'SDK_SOURCE', SDK, create=True), \
                patch.object(owner, 'identity_module', return_value=identity):
            self.assertEqual(owner.shared_tree(selected), tree)
            selected.export_patch = consumer
            with self.assertRaisesRegex(ValueError, 'different inputs'):
                owner.shared_tree(selected)
            selected.export_patch = str(producer)
            producer.write_text('#!/bin/sh\n# changed\n')
            with self.assertRaisesRegex(ValueError, 'different inputs'):
                owner.shared_tree(selected)
            producer.write_text('#!/bin/sh\n')
            (directory / identity.SHARED_EXPORT_DIRTY).write_text('interrupted\n')
            with self.assertRaisesRegex(ValueError, 'incomplete'):
                owner.shared_tree(selected)
            (directory / identity.SHARED_EXPORT_DIRTY).unlink()
            self.assertEqual(owner.shared_tree(selected), tree)
        self.assertEqual(stamps, [(path.stat().st_mtime_ns, path.stat().st_ino) for path in (receipt, tree)])
        work = Path(self.temp.name) / 'source'
        work.mkdir()
        (work / 'file').write_text('before\n')
        delta = b'--- file\n+++ file\n@@ -1 +1 @@\n-before\n+after\n'
        diff = Path(self.temp.name) / 'source.patch'
        diff.write_bytes(delta)
        self.run.stop()
        try:
            with patch.object(sourceprep.process, 'capture', wraps=sourceprep.process.capture) as capture:
                sourceprep.apply_patch(consumer, diff, delta, work, 'fixture', patch_args=('-p0', '-F0'))
                self.assertEqual(capture.call_args.args[0][0], consumer)
        finally:
            self.run.start()
        self.assertEqual((work / 'file').read_text(), 'after\n')

    def test_incomplete_update_is_never_accepted(self):
        directory = Path(self.temp.name) / 'export'
        identity.create_shared_export(directory, self.root, sys.executable, SDK, str(self.tool))
        (directory / identity.SHARED_EXPORT_DIRTY).write_text('interrupted\n')
        with self.assertRaisesRegex(ValueError, 'update is incomplete'):
            self.select(directory)

    def test_export_identity_covers_commits_overlays_and_patch_tool(self):
        before = identity.export_identity(self.root, sys.executable, SDK, str(self.tool))
        self.assertEqual(before['ports_commit'], 'a' * 40)
        self.assertEqual(before['upstream'], '1' * 40)
        self.assertEqual(before, identity.export_identity(self.root, sys.executable, SDK, str(self.tool)))
        # Package-specific identities keep their former digest input.
        self.assertEqual(identity.identity(self.root, 'cat/pkg', sys.executable, SDK)['package'], 'cat/pkg')
        changes = (lambda: self.pins.update(ports=b'b' * 40),
                   lambda: self.pins.update(upstream=b'2' * 40),
                   lambda: (self.root / 'pkgsrc/cat/pkg/Makefile').write_text('DISTNAME=changed\n'),
                   lambda: self.tool.write_text('#!/bin/sh\n# other patch\n'))
        for index, change in enumerate(changes):
            with self.subTest(change=index):
                previous = identity.export_identity(self.root, sys.executable, SDK, str(self.tool))
                change()
                self.assertNotEqual(previous, identity.export_identity(self.root, sys.executable, SDK, str(self.tool)))

    def test_shared_export_is_bound_to_current_inputs(self):
        directory = Path(self.temp.name) / 'export'
        receipt = identity.create_shared_export(directory, self.root, sys.executable, SDK, str(self.tool))
        self.assertEqual(len(self.exports), 1)
        self.assertEqual(receipt['identity']['ports_commit'], 'a' * 40)
        self.assertEqual(self.select(directory), directory / 'pkgsrc')
        self.assertEqual(len(self.exports), 1)
        with self.assertRaises(FileExistsError):
            identity.create_shared_export(directory, self.root, sys.executable, SDK, str(self.tool))
        self.pins.update(ports=b'b' * 40)
        self.assertEqual(self.select(directory), directory / 'pkgsrc')
        self.assertEqual(len(self.exports), 1)
        # The receipt keeps the commit that produced it as provenance even
        # though an unrelated HEAD-only change did not change export inputs.
        stored = json.loads((directory / identity.SHARED_EXPORT_RECEIPT).read_text())
        self.assertEqual(stored['identity']['ports_commit'], 'a' * 40)
        self.pins.update(ports=b'a' * 40)
        for change, undo in (
                (lambda: self.pins.update(upstream=b'2' * 40), lambda: self.pins.update(upstream=b'1' * 40)),
                (lambda: (self.root / 'pkgsrc/cat/pkg/Makefile').write_text('DISTNAME=changed\n'),
                 lambda: (self.root / 'pkgsrc/cat/pkg/Makefile').write_text('DISTNAME=example\n')),
                (lambda: self.tool.write_text('#!/bin/sh\n# other\n'), lambda: self.tool.write_text('#!/bin/sh\n'))):
            change()
            with self.assertRaisesRegex(ValueError, 'different inputs'):
                self.select(directory)
            undo()
        self.assertEqual(self.select(directory), directory / 'pkgsrc')
        (directory / 'pkgsrc/EMBERBSD-PKGSRC-REVISION').write_text('2' * 40 + '\n')
        with self.assertRaisesRegex(ValueError, 'differs from its receipt'):
            self.select(directory)
        (directory / identity.SHARED_EXPORT_RECEIPT).unlink()
        with self.assertRaisesRegex(ValueError, 'no receipt'):
            self.select(directory)

    def test_create_shared_export_allows_head_only_move(self):
        directory = Path(self.temp.name) / 'export-during-head-move'

        def export(command, **kwargs):
            tree = Path(command[3])
            (tree / 'cat/pkg').mkdir(parents=True)
            (tree / 'net/libfetch/files').mkdir(parents=True)
            (tree / 'EMBERBSD-PKGSRC-REVISION').write_text(self.pins['upstream'].decode() + '\n')
            self.pins['ports'] = b'b' * 40

        with patch.object(identity.subprocess, 'run', side_effect=export):
            receipt = identity.create_shared_export(directory, self.root, sys.executable,
                                                    SDK, str(self.tool))
        self.assertEqual(receipt['identity']['ports_commit'], 'a' * 40)
        self.assertEqual(self.select(directory), directory / 'pkgsrc')

    def test_receipt_format_is_checked(self):
        directory = Path(self.temp.name) / 'export'
        identity.create_shared_export(directory, self.root, sys.executable, SDK, str(self.tool))
        path = directory / identity.SHARED_EXPORT_RECEIPT
        receipt = json.loads(path.read_text())
        path.write_text(json.dumps({**receipt, 'format': 'other'}))
        with self.assertRaisesRegex(ValueError, 'invalid shared pkgsrc export receipt'):
            self.select(directory)

    def test_fingerprinted_stage_is_reused_and_ignores_unrelated_head(self):
        stage = load(self.root / 'scripts/pkgsrc-export-stage.py', 'stage_test')
        inputs = {'format': stage.FORMAT, 'version': stage.VERSION,
                  'upstream': '1' * 40, 'objects': {'pkgsrc/export.conf': 'a' * 40},
                  'patch': {'path': str(self.tool), 'sha256': 'b' * 64}}
        with patch.object(identity, '_pkgsrc_export_stage', return_value=stage), \
             patch.object(stage, 'fingerprint_inputs', return_value=inputs):
            key = stage.fingerprint(inputs)
            directory = Path(self.temp.name) / key
            tree = directory / 'pkgsrc'
            (tree / 'net/libfetch/files').mkdir(parents=True)
            (tree / 'EMBERBSD-PKGSRC-REVISION').write_text('1' * 40 + '\n')
            (directory / stage.RECEIPT).write_text(json.dumps({'fingerprint': key, 'inputs': inputs}))
            self.assertEqual(self.select(directory), tree)
            self.assertIsNone(identity.shared_export_material(directory, 'net/libfetch/files'))
            self.pins['ports'] = b'c' * 40  # unrelated HEAD movement does not change Git input keys
            self.assertEqual(self.select(directory), tree)
            changed = dict(inputs, objects={'pkgsrc/export.conf': 'd' * 40})
            with patch.object(stage, 'fingerprint_inputs', return_value=changed):
                with self.assertRaisesRegex(ValueError, 'different inputs'):
                    self.select(directory)
        self.assertEqual(len(self.exports), 0)

    def test_stage_receipt_symlink_is_rejected(self):
        directory = Path(self.temp.name) / 'stage'
        directory.mkdir()
        target = Path(self.temp.name) / 'receipt'
        target.write_text('{}')
        (directory / 'pkgsrc-stage.json').symlink_to(target)
        with self.assertRaisesRegex(ValueError, 'invalid pkgsrc export stage receipt'):
            self.select(directory)

    def test_corrupt_stage_receipt_is_rejected(self):
        stage = load(self.root / 'scripts/pkgsrc-export-stage.py', 'stage_corrupt_test')
        inputs = {'format': stage.FORMAT, 'version': stage.VERSION,
                  'upstream': '1' * 40, 'objects': {'pkgsrc/export.conf': 'a' * 40},
                  'patch': {'path': str(self.tool), 'sha256': 'b' * 64}}
        directory = Path(self.temp.name) / stage.fingerprint(inputs)
        directory.mkdir()
        (directory / stage.RECEIPT).write_text('{broken')
        with patch.object(identity, '_pkgsrc_export_stage', return_value=stage), \
             patch.object(stage, 'fingerprint_inputs', return_value=inputs):
            with self.assertRaises(ValueError):
                self.select(directory)


class OwnerTest(unittest.TestCase):
    """Each common source owner verifies against the shared export only."""

    def owner(self, name):
        module = load(ROOT / f'scripts/source-inputs/{name}/source.py', name + '_owner')
        if hasattr(module, 'load_sdk'):
            module.load_sdk(['--sdk-source', str(SDK)])
        return module

    def test_legacy_owners_share_selected_export_and_keep_default(self):
        from emberbsd_sdk.errors import SDKError
        with tempfile.TemporaryDirectory(dir=WORK) as temp:
            tree = Path(temp) / 'selected-tree'
            for name in ('tdb', 'ppp', 'libpcap', 'tcp_wrappers', 'libevent'):
                with self.subTest(owner=name):
                    owner = self.owner(name)
                    selector = load(ROOT / 'scripts/pkgsrc-source-identity.py', 'selector')
                    old = {'export': {'api': 1, 'package': owner.PACKAGE,
                           'export_inputs_sha256': '1' * 64, 'upstream': '2' * 40},
                           'owner_sha256': '3' * 64}
                    current = {'export': {'upstream': '2' * 40}, 'owner_sha256': '4' * 64}
                    with patch.object(owner, 'source_identity', return_value=current), \
                         patch.object(owner.jsonio, 'read_json', return_value={'identity': old}), \
                         patch.object(owner.sourceprep, 'validate_prepared_tree', return_value={'tree_sha256': '5' * 64}), \
                         patch.object(owner, 'identity_module', return_value=selector), \
                         patch.object(selector, 'shared_export', return_value=tree) as shared, \
                         patch.object(owner, 'prepare', return_value={'tree_sha256': '5' * 64}) as prepare:
                        owner.verify('/source', sys.executable, archive='/archive', patch='/patch', pkgsrc_export='/export')
                        self.assertEqual(prepare.call_args.kwargs['exported'], tree)
                        shared.assert_called_once_with('/export', owner.PORTS, sys.executable, owner.SDK_SOURCE, '/patch')
                        owner.verify('/source', sys.executable, archive='/archive', patch='/patch')
                        self.assertIsNone(prepare.call_args.kwargs['exported'])
                        shared.side_effect = SDKError('invalid shared export')
                        with self.assertRaisesRegex(SDKError, 'invalid shared export'):
                            owner.verify('/source', sys.executable, archive='/archive', patch='/patch', pkgsrc_export='/invalid')

    def test_libfetch_reads_small_filesdir_for_stage_without_material_snapshot(self):
        owner = self.owner('libfetch')
        owner.SDK_SOURCE = SDK
        with tempfile.TemporaryDirectory(dir=WORK) as temp:
            stage = Path(temp) / 'stage'
            stage.mkdir()
            inputs = {'format': 'emberbsd-pkgsrc-export-stage', 'version': 1}
            key = hashlib.sha256(
                json.dumps(inputs, sort_keys=True, separators=(',', ':')).encode('ascii')).hexdigest()
            (stage / 'pkgsrc-stage.json').write_text(
                json.dumps({'fingerprint': key, 'inputs': inputs}))
            tree = stage / 'pkgsrc'
            files = tree / 'net/libfetch/files'
            files.mkdir(parents=True)
            (files / 'fetch.c').write_text('common source')
            with patch.object(owner, 'identity_module', return_value=identity), \
                 patch.object(identity, 'shared_export', return_value=tree):
                selected, snapshot = owner.export_tree(temp, sys.executable, '/patch', str(stage))
            self.assertEqual(selected, tree)
            self.assertEqual(snapshot, identity.material_snapshot(files))

    def test_scoped_owners_keep_one_default_export(self):
        for name in ('tdb', 'ppp', 'libpcap', 'tcp_wrappers'):
            with self.subTest(owner=name):
                owner = self.owner(name)
                selector = load(ROOT / 'scripts/pkgsrc-source-identity.py', 'selector')
                effective = {'api': 1, 'package': owner.PACKAGE,
                             'effective_package_sha256': '4' * 64, 'upstream': '1' * 40}
                old = {'effective': effective, 'owner_sha256': '2' * 64}
                current = {'export': {'upstream': '1' * 40}, 'owner_sha256': '3' * 64}
                with patch.object(owner, 'source_identity', return_value=current), \
                     patch.object(owner.jsonio, 'read_json', return_value={'identity': old}), \
                     patch.object(owner.sourceprep, 'validate_prepared_tree', return_value={'tree_sha256': '5' * 64}), \
                     patch.object(owner, 'identity_module', return_value=selector), \
                     patch.object(selector, 'effective_package_identity', return_value=effective), \
                     patch.object(owner.process, 'capture') as capture, \
                     patch.object(owner, 'prepare', return_value={'tree_sha256': '5' * 64}) as prepare:
                    owner.verify('/source', sys.executable, archive='/archive', patch='/patch')
                    self.assertEqual(capture.call_count, 1)
                    self.assertEqual(prepare.call_args.kwargs['exported'], Path(capture.call_args.args[0][3]))

    def test_git_identity_receipts_verify_without_an_export(self):
        """An API 2 receipt naming the current Git objects needs no export."""
        for name in GIT_OWNERS:
            with self.subTest(owner=name):
                owner = self.owner(name)
                selector = load(ROOT / 'scripts/pkgsrc-source-identity.py', 'selector')
                effective = {'api': 2, 'package': owner.PACKAGE,
                             'effective_package_sha256': '4' * 64, 'upstream': '1' * 40}
                old = {'effective': effective, 'owner_sha256': '3' * 64}
                current = {'export': {'upstream': '1' * 40}, 'owner_sha256': '3' * 64}
                record = {'tree_sha256': '5' * 64}
                with patch.object(owner, 'source_identity', return_value=current), \
                     patch.object(owner.jsonio, 'read_json', return_value={'identity': old}), \
                     patch.object(owner.sourceprep, 'validate_prepared_tree', return_value=record), \
                     patch.object(owner, 'identity_module', return_value=selector), \
                     patch.object(owner, 'git_effective_identity', return_value=dict(effective, api=3, legacy_api2_sha256=effective['effective_package_sha256'])) as git_identity, \
                     patch.object(selector, 'effective_package_identity', return_value=dict(effective, api=1)), \
                     patch.object(selector, 'shared_export') as shared, \
                     patch.object(owner.process, 'capture') as capture, \
                     patch.object(owner, 'prepare', return_value=record) as prepare:
                    accepted = inspect.signature(owner.verify).parameters
                    extra = {'lzip': '/lzip'} if 'lzip' in accepted else {}
                    shared_args = {'pkgsrc_export': '/export'} if 'pkgsrc_export' in accepted else {}
                    self.assertEqual(owner.verify('/source', sys.executable, **shared_args), record)
                    git_identity.assert_called_once_with(sys.executable)
                    # A given shared export is still checked, once; nothing is exported or prepared.
                    self.assertEqual((capture.call_count, shared.call_count, prepare.call_count),
                                     (0, len(shared_args), 0))
                    # A changed dependent Git object falls back to the payload comparison.
                    git_identity.return_value = dict(effective, api=3, legacy_api2_sha256='6' * 64)
                    owner.verify('/source', sys.executable, archive='/archive', patch='/patch', **extra)
                    self.assertEqual((capture.call_count, prepare.call_count), (1, 1))
                    # So does a changed owner.
                    git_identity.return_value = dict(effective, api=3, legacy_api2_sha256=effective['effective_package_sha256'])
                    current['owner_sha256'] = '7' * 64
                    owner.verify('/source', sys.executable, archive='/archive', patch='/patch', **extra)
                    self.assertEqual((capture.call_count, prepare.call_count), (2, 2))

    def test_git_identity_receipts_refuse_a_broken_shared_export(self):
        """An unchanged API 2 receipt does not let a broken shared export pass."""
        owners = [name for name in GIT_OWNERS
                  if 'pkgsrc_export' in inspect.signature(self.owner(name).verify).parameters]
        self.assertGreaterEqual(len(owners), 18)
        for name in owners:
            with self.subTest(owner=name):
                owner = self.owner(name)
                selector = load(ROOT / 'scripts/pkgsrc-source-identity.py', 'selector')
                effective = {'api': 2, 'package': owner.PACKAGE,
                             'effective_package_sha256': '4' * 64, 'upstream': '1' * 40}
                old = {'effective': effective, 'owner_sha256': '3' * 64}
                current = {'export': {'upstream': '1' * 40}, 'owner_sha256': '3' * 64}
                with patch.object(owner, 'source_identity', return_value=current), \
                     patch.object(owner.jsonio, 'read_json', return_value={'identity': old}), \
                     patch.object(owner.sourceprep, 'validate_prepared_tree', return_value={'tree_sha256': '5' * 64}), \
                     patch.object(owner, 'identity_module', return_value=selector), \
                     patch.object(owner, 'git_effective_identity', return_value=dict(effective, api=3, legacy_api2_sha256=effective['effective_package_sha256'])), \
                     patch.object(selector, 'shared_export',
                                  side_effect=ValueError('invalid shared pkgsrc export receipt')):
                    with self.assertRaisesRegex(ValueError, 'invalid shared pkgsrc export receipt'):
                        owner.verify('/source', sys.executable, patch='/patch', pkgsrc_export='/export')
        libarchive = load(ROOT / 'scripts/libarchive-source.py', 'libarchive_owner')
        selector = load(ROOT / 'scripts/pkgsrc-source-identity.py', 'selector')
        with patch.object(libarchive, 'module', return_value=selector), \
             patch.object(selector, 'shared_export', side_effect=ValueError('invalid shared pkgsrc export receipt')), \
             patch.object(libarchive, 'selected_identity', side_effect=AssertionError('export checked too late')):
            with self.assertRaisesRegex(ValueError, 'invalid shared pkgsrc export receipt'):
                libarchive.verify('/source', str(SDK), sys.executable, '/patch', '/export')

    def test_prepare_uses_the_selected_shared_export(self):
        for name in GIT_OWNERS:
            with self.subTest(owner=name):
                owner = self.owner(name)
                selector = load(ROOT / 'scripts/pkgsrc-source-identity.py', 'selector')
                argv = ['--git', sys.executable, 'prepare', '--archive', '/archive', '--output', '/output',
                        '--patch', '/patch', '--scoped-identity', '--pkgsrc-export', '/export']
                if name == 'rcs':
                    argv[argv.index('--scoped-identity'):argv.index('--scoped-identity')] = ['--lzip', '/lzip']
                with patch.object(owner, 'load_sdk', return_value=argv), \
                     patch.object(owner, 'identity_module', return_value=selector), \
                     patch.object(selector, 'shared_export', return_value=Path('/tree')) as shared, \
                     patch.object(owner, 'prepare', return_value={}) as prepare, \
                     patch.object(owner.sys.stdout.buffer, 'write'):
                    owner.main()
                    shared.assert_called_once_with('/export', owner.PORTS, sys.executable, owner.SDK_SOURCE, '/patch')
                    self.assertEqual(prepare.call_args.kwargs['exported'], Path('/tree'))

    def test_owners_use_the_shared_export_without_exporting(self):
        with tempfile.TemporaryDirectory(dir=WORK) as temp:
            shared = Path(temp) / 'shared'
            for name in OWNERS:
                with self.subTest(owner=name):
                    owner = self.owner(name)
                    effective = {'api': 1, 'package': owner.PACKAGE,
                                 'effective_package_sha256': '4' * 64, 'upstream': '1' * 40}
                    old = {'effective': effective, 'owner_sha256': '3' * 64}
                    selector = load(ROOT / 'scripts/pkgsrc-source-identity.py', 'selector')
                    calls = []
                    def select(*args):
                        calls.append(args)
                        return Path(temp) / 'tree'
                    def capture(command, **kwargs):
                        raise AssertionError('owner exported pkgsrc itself: ' + ' '.join(map(str, command)))
                    with patch.object(owner, 'source_identity', return_value={'export': {'upstream': '1' * 40}, 'owner_sha256': '3' * 64}), \
                            patch.object(owner.jsonio, 'read_json', return_value={'identity': old}), \
                            patch.object(owner.sourceprep, 'validate_prepared_tree', return_value={'tree_sha256': '5' * 64}), \
                            patch.object(owner, 'identity_module', return_value=selector), \
                            patch.object(selector, 'shared_export', side_effect=select), \
                            patch.object(selector, 'effective_package_identity', return_value=effective), \
                            patch.object(owner.process, 'capture', side_effect=capture):
                        record = owner.verify(str(Path(temp) / 'source'), sys.executable,
                                              patch='/selected/patch', pkgsrc_export=str(shared))
                    self.assertEqual(record, {'tree_sha256': '5' * 64})
                    self.assertEqual([call[0] for call in calls], [str(shared)])
                    self.assertEqual(calls[0][4], '/selected/patch')

    def test_changed_owners_compare_against_the_selected_export_without_exporting_again(self):
        # When the owner or the effective recipe changed, verify prepares the
        # expected payload from the archive. It must use the export it already
        # selected (shared or its own) instead of exporting pkgsrc once more.
        class Stop(Exception):
            pass
        names = sorted(path.parent.name for path in (ROOT / 'scripts/source-inputs').glob('*/source.py')
                       if 'exported=exported)' in path.read_text() or path.parent.name == 'libpcap')
        self.assertTrue(set(OWNERS) <= set(names), names)
        with tempfile.TemporaryDirectory(dir=WORK) as temp:
            temp = Path(temp).resolve()
            for name in names:
                with self.subTest(owner=name):
                    owner = self.owner(name)
                    selector = load(ROOT / 'scripts/pkgsrc-source-identity.py', 'selector')
                    effective = {'api': 1, 'package': owner.PACKAGE,
                                 'effective_package_sha256': '4' * 64, 'upstream': '1' * 40}
                    old = {'effective': effective, 'owner_sha256': '2' * 64}
                    tree = temp / 'shared-tree'
                    prepared = []
                    def prepare(*args, **kwargs):
                        prepared.append(kwargs.get('exported'))
                        return {'tree_sha256': '5' * 64}
                    exports = []
                    def capture(command, **kwargs):
                        raise AssertionError('owner exported pkgsrc itself: ' + ' '.join(map(str, command)))
                    def own_export(command, **kwargs):
                        # Owners without --pkgsrc-export make one export of their own.
                        self.assertTrue(str(command[2]).endswith('prepare-pkgsrc.py'), command)
                        exports.append(Path(command[3]))
                    extra = {'lzip': '/selected/lzip'} if name == 'rcs' else {}
                    shared = 'pkgsrc_export' in inspect.signature(owner.verify).parameters
                    if shared:
                        extra['pkgsrc_export'] = str(temp / 'shared')
                    with patch.object(owner, 'source_identity', return_value={'export': {'upstream': '1' * 40}, 'owner_sha256': '3' * 64}), \
                            patch.object(owner.jsonio, 'read_json', return_value={'identity': old}), \
                            patch.object(owner.sourceprep, 'validate_prepared_tree', return_value={'tree_sha256': '5' * 64}), \
                            patch.object(owner, 'identity_module', return_value=selector), \
                            patch.object(selector, 'shared_export', return_value=tree), \
                            patch.object(selector, 'effective_package_identity', return_value=effective), \
                            patch.object(owner, 'prepare', side_effect=prepare), \
                            patch.object(owner.process, 'capture', side_effect=capture if shared else own_export):
                        owner.verify(str(temp / 'source'), sys.executable, archive='/selected/archive',
                                     patch='/selected/patch', **extra)
                    self.assertEqual(prepared, [tree] if shared else exports)
                    self.assertEqual(len(exports), 0 if shared else 1)
                    # prepare itself reads the given export and does not make one.
                    seen = []
                    def recipe(exported):
                        seen.append(exported)
                        raise Stop()
                    arguments = [str(temp / 'archive'), temp / f'expected-{name}', '/selected/patch', sys.executable]
                    if name == 'wpa':
                        arguments.insert(1, str(temp / 'hostapd-archive'))
                    if name == 'rcs':
                        arguments.append('/selected/lzip')
                    with patch.object(owner, 'source_identity', return_value={'export': {'upstream': '1' * 40}, 'owner_sha256': '3' * 64}), \
                            patch.object(owner, 'recipe', side_effect=recipe), \
                            patch.object(owner.process, 'capture', side_effect=capture), \
                            self.assertRaises(Stop):
                        owner.prepare(*arguments, exported=tree)
                    self.assertEqual(seen, [tree])

    def test_libarchive_uses_the_shared_export_without_exporting(self):
        owner = load(ROOT / 'scripts/libarchive-source.py', 'libarchive_owner')
        selector = load(ROOT / 'scripts/pkgsrc-source-identity.py', 'selector')
        effective = {'api': 1, 'package': owner.PACKAGE, 'effective_package_sha256': '4' * 64, 'upstream': '1' * 40}
        old = {'effective': effective, 'owner_sha256': '3' * 64}
        from emberbsd_sdk import jsonio, sourceprep
        with tempfile.TemporaryDirectory(dir=WORK) as temp, \
                patch.object(owner, 'selected_identity', return_value={'upstream': '1' * 40, 'owner_sha256': '3' * 64}), \
                patch.object(jsonio, 'read_json', return_value={'identity': old}), \
                patch.object(sourceprep, 'validate_prepared_tree', return_value={'tree_sha256': '5' * 64}), \
                patch.object(owner, 'module', return_value=selector), \
                patch.object(selector, 'shared_export', return_value=Path('/unused/tree')) as select, \
                patch.object(selector, 'effective_package_identity', return_value=effective), \
                patch.object(owner.subprocess, 'run', side_effect=AssertionError('owner exported pkgsrc itself')):
            record = owner.verify(str(Path(temp) / 'source'), str(SDK), sys.executable,
                                  '/selected/patch', str(Path(temp) / 'shared'))
        self.assertEqual(record, {'tree_sha256': '5' * 64})
        self.assertEqual(select.call_count, 1)


if __name__ == '__main__':
    unittest.main()
