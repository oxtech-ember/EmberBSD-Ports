#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted), native builder contracts.
"""Exercise orchestration fixtures, not upstream KDocTools or target builds."""

import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import subprocess
import shutil
import tarfile
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
PORTS = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PORTS / 'pkgsrc/lang/llvm/files'))
import sdk_source


def load_builder():
    path = PORTS / 'probes/plasma-mobile/toolkit/cross/build-doctools-host.py'
    spec = importlib.util.spec_from_file_location('doctools_builder', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BuilderTests(unittest.TestCase):
    def setUp(self):
        from emberbsd_sdk.inventory import sha256_file
        self.builder = load_builder()
        self.root = Path(tempfile.mkdtemp(prefix='doctools-contract-')).resolve()
        self.retain = False
        self.addCleanup(self.cleanup_work)
        self.source = self.root / 'ports'
        self.dist = self.root / 'distfiles'
        self.qt, self.native, self.ecm = [self.root / name for name in ('qt', 'native', 'ecm')]
        self.work = self.root / 'new-work'
        self.table = self.source / 'probes/plasma-mobile/toolkit/sources.tsv'
        self.table.parent.mkdir(parents=True)
        for directory in (self.dist, self.qt / 'bin', self.native, self.ecm, self.root / 'tools'):
            directory.mkdir(parents=True)
        self.environment = dict(os.environ)
        self.environment.update(JOBS='3', PERL5LIB='/explicit/perl/modules')
        for name in ('CMAKE', 'NINJA', 'HOST_CC', 'HOST_CXX', 'HOST_PERL'):
            path = self.root / 'tools' / name.lower()
            path.write_text('#!/bin/sh\nexit 0\n')
            path.chmod(0o755)
            self.environment[name] = str(path)
        (self.qt / 'bin/qmake').write_text('#!/bin/sh\nexit 0\n')
        (self.qt / 'bin/qmake').chmod(0o755)
        rows = []
        for component in ('karchive', 'kdoctools'):
            archive = self.dist / (component + '-6.31.0.tar.xz')
            with tarfile.open(archive, 'w:xz') as output:
                info = tarfile.TarInfo(component + '-6.31.0/CMakeLists.txt')
                body = b'# Command fixture, not upstream source.\n'
                info.size = len(body)
                output.addfile(info, io.BytesIO(body))
            rows.append('fixture/' + component + '\t' + archive.name + '\t' + sha256_file(archive)
                        + '\thttps://example.invalid/' + archive.name)
        self.table.write_text('\n'.join(rows) + '\n')
        self.calls = []
        self.qt_version = '6.12.0'
        self.header_version = '6.31.0'
        self.omit_program = None
        self.fail_step = None
        self.mutate_tool = False
        self.addCleanup(patch.stopall)
        patch.object(self.builder, 'PORTS', self.source).start()
        patch.dict(os.environ, self.environment, clear=True).start()
        patch('emberbsd_sdk.provenance.git_source', side_effect=lambda root, **kw:
              dict(path=root, commit='1' * 40, external_gitlinks=[])).start()
        from emberbsd_sdk.process import run_logged
        self.real_run_logged = run_logged
        patch('emberbsd_sdk.process.run_logged', side_effect=self.run_fixture).start()

    def cleanup_work(self):
        if self.retain:
            print('Retained native fixture after failure: ' + str(self.root), file=sys.stderr)
        else:
            shutil.rmtree(self.root)

    def run_fixture(self, argv, log, **kwargs):
        from emberbsd_sdk.errors import CommandError, ProcessOwnershipError
        name = Path(log).stem
        self.calls.append((name, argv, kwargs))
        Path(log).write_text('fixture ' + name + '\n')
        if name == self.fail_step:
            raise CommandError(23, argv)
        if self.fail_step == 'ownership' and name == 'archive-build':
            raise ProcessOwnershipError(12345, 'fixture shutdown is unproven')
        if name == 'qt-version':
            Path(log).write_text(self.qt_version + '\n')
        if name == 'doctools-configure':
            (self.work / 'doctools/src').mkdir(parents=True)
            (self.work / 'doctools/src/kdoctools_version.h').write_text(
                '#define KDOCTOOLS_VERSION_STRING "' + self.header_version + '"\n')
        if name == 'doctools-install':
            (self.work / 'prefix/bin').mkdir(parents=True)
            (self.work / 'prefix/share').mkdir()
            for program in self.builder.PROGRAMS:
                if program == self.omit_program:
                    continue
                path = self.work / 'prefix/bin' / program
                path.write_text('#!/bin/sh\nprintf "meinproc6 5.0\\n"\n')
                path.chmod(0o755)
            if self.mutate_tool:
                Path(self.environment['CMAKE']).write_text('changed tool\n')
        if name == 'meinproc-version':
            Path(log).write_text('meinproc6 5.0\n')

    def build(self):
        self.builder.build(list(map(str, (self.dist, self.qt, self.native, self.ecm, self.work))), SDK_ROOT)

    def test_preserved_commands_and_bound_receipt(self):
        from emberbsd_sdk.inventory import sha256_file
        self.build()
        commands = {name: argv for name, argv, env in self.calls}
        common = ('-DBUILD_TESTING=OFF', '-DCMAKE_BUILD_TYPE=Release', '-G')
        for step in ('archive-configure', 'doctools-configure'):
            for flag in common:
                self.assertIn(flag, commands[step])
            self.assertIn('-DCMAKE_C_COMPILER=' + self.environment['HOST_CC'], commands[step])
            self.assertIn('-DCMAKE_CXX_COMPILER=' + self.environment['HOST_CXX'], commands[step])
        self.assertNotIn('-DCMAKE_DISABLE_FIND_PACKAGE_KF6I18n=ON', commands['archive-configure'])
        self.assertNotIn('-DPERL_EXECUTABLE=' + self.environment['HOST_PERL'], commands['archive-configure'])
        self.assertIn('-DPERL_EXECUTABLE=' + self.environment['HOST_PERL'], commands['doctools-configure'])
        for flag in ('-DCMAKE_DISABLE_FIND_PACKAGE_KF6I18n=ON', '-DINSTALL_INTERNAL_TOOLS=ON',
                     '-DDocBookXML4_DTD_DIR=' + str(self.native / 'share/xml/docbook/4.5'),
                     '-DDOCBOOKXSL_DIR=' + str(self.native / 'share/xsl/docbook')):
            self.assertIn(flag, commands['doctools-configure'])
        self.assertEqual(commands['archive-build'][-2:], ['--parallel', '3'])
        result = json.loads((self.work / 'outputs.json').read_text())
        self.assertEqual(result['inputs_sha256'], sha256_file(self.work / 'inputs.json'))
        self.assertEqual(set(result['logs']), {name + '.log' for name in commands})
        self.assertFalse((self.work / 'incomplete.json').exists())
        for program in self.builder.PROGRAMS:
            self.assertEqual(result['prefix']['bin/' + program]['sha256'],
                             sha256_file(self.work / 'prefix/bin' / program))
        self.assertEqual((self.work / 'prefix/share/ember-doctools-version').read_text(), '6.31.0\n')
        self.assertEqual((self.work / 'version.txt').read_text(), 'meinproc6 5.0\n')
        inputs = json.loads((self.work / 'inputs.json').read_text())
        self.assertEqual(inputs['environment']['PERL5LIB'], '/explicit/perl/modules')
        self.assertEqual(inputs['python']['sha256'], sha256_file(Path(sys.executable).resolve()))
        self.assertIn('not sealed', inputs['boundary'])
        self.assertTrue(all(call[2]['cwd'] == str(self.work) for call in self.calls))
        self.assertTrue(all(call[2]['empty_snapshot_timeout'] == 120 for call in self.calls))

    def test_wrong_pin_does_not_create_work_or_run(self):
        with (self.dist / 'karchive-6.31.0.tar.xz').open('ab') as stream:
            stream.write(b'changed')
        with self.assertRaisesRegex(ValueError, 'Wrong archive SHA256'):
            self.build()
        self.assertFalse(self.work.exists())
        self.assertEqual(self.calls, [])

    def test_duplicate_pin_rejected(self):
        self.table.write_text(self.table.read_text() * 2)
        with self.assertRaisesRegex(ValueError, 'duplicate source pin'):
            self.build()
        self.assertFalse(self.work.exists())

    def test_existing_and_overlapping_work_preserved(self):
        self.work.mkdir()
        marker = self.work / 'owned'
        marker.write_bytes(b'keep')
        with self.assertRaisesRegex(ValueError, 'must not exist'):
            self.build()
        self.assertEqual(marker.read_bytes(), b'keep')
        self.work = self.native / 'child'
        with self.assertRaisesRegex(Exception, 'overlapping input/output'):
            self.build()
        self.assertFalse(self.work.exists())

    def test_busy_work_and_native_locks(self):
        from emberbsd_sdk.process import ContextLocks
        for path in (self.work, self.native):
            with self.subTest(path=path), ContextLocks([str(path)], str(self.root)):
                with self.assertRaisesRegex(Exception, 'context is busy'):
                    self.build()
                self.assertFalse(self.work.exists())

    def test_wrong_qt_stops_before_extract_and_configure(self):
        self.qt_version = '6.11.0'
        with self.assertRaisesRegex(ValueError, 'Qt 6.12.0'):
            self.build()
        self.assertEqual([call[0] for call in self.calls], ['qt-version'])
        self.assertEqual(list((self.work / 'source').iterdir()), [])
        self.assertFalse((self.work / 'outputs.json').exists())

    def test_qt_locale_warning_preserves_exact_version_check(self):
        self.qt_version = ('Detected locale "C" with character encoding "US-ASCII", which is not UTF-8.\n'
                           'Qt depends on a UTF-8 locale, and has switched to "UTF-8" instead.\n'
                           'If this causes problems, reconfigure your locale. See the locale(1) manual\n'
                           'for more information.\n6.12.0')
        self.build()
        self.assertTrue((self.work / 'outputs.json').exists())

    def test_duplicate_qt_version_lines_rejected(self):
        self.qt_version = '6.12.0\n6.12.0'
        with self.assertRaisesRegex(ValueError, 'Qt 6.12.0'):
            self.build()
        self.assertEqual([call[0] for call in self.calls], ['qt-version'])

    def test_producer_failure_stops_and_retains_incomplete(self):
        from emberbsd_sdk.errors import CommandError
        self.fail_step = 'archive-build'
        with self.assertRaises(CommandError) as caught:
            self.build()
        self.assertEqual(caught.exception.returncode, 23)
        self.assertEqual(self.calls[-1][0], 'archive-build')
        self.assertTrue((self.work / 'incomplete.json').exists())
        self.assertFalse((self.work / 'outputs.json').exists())

    def test_unproven_shutdown_is_quarantined(self):
        from emberbsd_sdk.errors import ProcessOwnershipError
        self.fail_step = 'ownership'
        with self.assertRaises(ProcessOwnershipError):
            self.build()
        receipt = json.loads((self.work / sdk_source.PRODUCER_QUARANTINE).read_text())
        self.assertEqual(receipt['session_id'], 12345)
        self.assertFalse((self.work / 'outputs.json').exists())
        self.assertTrue((self.work / 'incomplete.json').exists())

    def test_missing_generator_rejected(self):
        self.omit_program = 'docbookl10nhelper'
        with self.assertRaisesRegex(Exception, 'No such file|expected|No such'):
            self.build()
        self.assertFalse((self.work / 'outputs.json').exists())

    def test_old_frameworks_header_rejected_despite_tool_banner(self):
        self.header_version = '6.30.0'
        with self.assertRaisesRegex(ValueError, 'configured Frameworks version'):
            self.build()
        self.assertFalse((self.work / 'prefix/share/ember-doctools-version').exists())
        self.assertFalse((self.work / 'outputs.json').exists())

    def test_changed_tool_cannot_seal_outputs(self):
        self.mutate_tool = True
        with self.assertRaisesRegex(ValueError, 'Native tool changed'):
            self.build()
        self.assertFalse((self.work / 'outputs.json').exists())
        self.assertTrue((self.work / 'incomplete.json').exists())
        self.assertFalse((self.work / 'prefix/share/ember-doctools-version').exists())
        self.assertFalse((self.work / 'tooling/KF6DocTools/KF6DocToolsToolsTargets.cmake').exists())

    def test_late_failure_does_not_publish_consumer_marker(self):
        from emberbsd_sdk.jsonio import write_json
        from emberbsd_sdk.inventory import snapshot_installed_tree
        cases = ('inventory', 'receipt', 'marker')
        for case in cases:
            with self.subTest(case=case):
                self.work = self.root / ('work-' + case)
                def snapshot(path):
                    if case == 'inventory':
                        raise OSError('fixture inventory failure')
                    return snapshot_installed_tree(path)
                def write(path, value, **kwargs):
                    if case == 'receipt' and Path(path).name == 'outputs.json':
                        raise OSError('fixture receipt failure')
                    return write_json(path, value, **kwargs)
                def link(source, destination):
                    raise OSError('fixture marker publication failure')
                with patch('emberbsd_sdk.inventory.snapshot_installed_tree', side_effect=snapshot), \
                     patch('emberbsd_sdk.jsonio.write_json', side_effect=write), \
                     patch.object(self.builder.os, 'link', side_effect=link):
                    with self.assertRaisesRegex(OSError, 'fixture'):
                        self.build()
                self.assertFalse((self.work / 'prefix/share/ember-doctools-version').exists())
                self.assertTrue((self.work / 'incomplete.json').exists())

    def test_cli_sdk_selection_and_help(self):
        script = PORTS / 'probes/plasma-mobile/toolkit/cross/build-doctools-host.py'
        environment = dict(os.environ)
        environment.pop('EMBERBSD_SDK_SOURCE', None)
        missing = subprocess.run([sys.executable, '-B', str(script), '--help'], env=environment,
                                 capture_output=True, text=True, timeout=20)
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn('absolute SDK source', missing.stderr)
        valid = subprocess.run([sys.executable, '-B', str(script), '--sdk-source', SDK_ROOT, '--help'],
                               capture_output=True, text=True, timeout=20)
        self.assertEqual(valid.returncode, 0, valid.stderr)
        self.assertIn('distfiles host_qt native_prefix ecm_cmake_dir new_work', ' '.join(valid.stdout.split()))
        wrong = self.root / 'wrong-sdk/src/emberbsd_sdk'
        wrong.mkdir(parents=True)
        (wrong / '__init__.py').write_text('API_VERSION = 999\n')
        rejected = subprocess.run([sys.executable, '-B', str(script), '--sdk-source', str(wrong.parents[1]),
                                   '--help'], capture_output=True, text=True, timeout=20)
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn('API version 1', rejected.stderr)
        self.assertFalse(self.work.exists())

    @unittest.skipUnless(os.environ.get('DOCTOOLS_NATIVE_PROCESS_TEST') == '1',
                         'Set DOCTOOLS_NATIVE_PROCESS_TEST=1 for the actual SDK process fixture')
    def test_actual_sdk_process_fixture(self):
        # Real SDK subprocess/lock/log path. The executable writes only fixtures;
        # it neither invokes a compiler nor builds any prerequisite package.
        driver = """import pathlib, sys
args = sys.argv[1:]
if args == ['-query', 'QT_VERSION']:
    print('6.12.0')
elif '--version' in args:
    print('native command fixture 1')
elif '-S' in args:
    build = pathlib.Path(args[args.index('-B') + 1])
    (build / 'src').mkdir(parents=True)
    (build / 'src/kdoctools_version.h').write_text('#define KDOCTOOLS_VERSION_STRING "6.31.0"\\n')
elif '--install' in args and args[-1].endswith('/doctools'):
    prefix = pathlib.Path(args[-1]).parent / 'prefix'
    (prefix / 'bin').mkdir(parents=True)
    (prefix / 'share').mkdir()
    for name in ('meinproc6', 'checkXML6', 'docbookl10nhelper'):
        path = prefix / 'bin' / name
        path.write_text('#!' + sys.executable + '\\nprint("meinproc6 5.0")\\n')
        path.chmod(0o755)
"""
        for path in [*(Path(value) for value in (self.environment[name] for name in
                                                ('CMAKE', 'NINJA', 'HOST_CC', 'HOST_CXX', 'HOST_PERL'))),
                     self.qt / 'bin/qmake']:
            path.write_text('#!' + sys.executable + '\n' + driver)
        self.retain = True
        try:
            with patch('emberbsd_sdk.process.run_logged', self.real_run_logged):
                self.build()
        finally:
            evidence = os.environ.get('DOCTOOLS_TEST_RECEIPTS')
            if evidence:
                destination = Path(evidence) / 'native-fixture'
                shutil.copytree(self.root, destination, symlinks=True)
                (destination / 'boundary.txt').write_text(
                    'Actual SDK processes; synthetic archives/commands and mocked Git provenance.\n'
                    'No compiler, upstream package build or target acceptance.\n')
        self.retain = False
        self.assertTrue((self.work / 'outputs.json').is_file())
        self.assertFalse((self.work / sdk_source.PRODUCER_QUARANTINE).exists())
        self.assertEqual((self.work / 'version.txt').read_text(), 'meinproc6 5.0\n')

    def test_unsafe_archive_rejected_before_extraction(self):
        archive = self.root / 'bad.tar.xz'
        for name, kind in (('../outside', tarfile.REGTYPE), ('karchive-6.31.0/link', tarfile.SYMTYPE)):
            with self.subTest(name=name):
                with tarfile.open(archive, 'w:xz') as output:
                    info = tarfile.TarInfo(name)
                    info.type = kind
                    info.linkname = '/outside'
                    output.addfile(info, io.BytesIO())
                with self.assertRaisesRegex(ValueError, 'Unexpected source archive member'):
                    self.builder.extract(archive, self.root / 'never-created', 'karchive')
                self.assertFalse((self.root / 'never-created').exists())


if __name__ == '__main__':
    SDK_ROOT, arguments = sdk_source.load_sdk()
    unittest.main(argv=[sys.argv[0], *arguments])
