#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted adapter regressions.
"""Subprocess checks for the native pkgsrc metadata adapter."""
import json
import hashlib
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'export-build-graph.py'


class ExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sdk_source = os.environ['EMBERBSD_SDK_SOURCE']

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.pkgsrc = self.path / 'pkgsrc'
        self.pkgsrc.mkdir()
        (self.pkgsrc / 'shared.mk').write_text('SHARED=yes\n')
        self.packages = {
            'devel/app': {'TOOL_DEPENDS': 'generator>=2:../../devel/generator',
                          'BUILD_DEPENDS': 'library>=1:../../devel/library',
                          'DEPENDS': 'runtime>=1:../../devel/runtime',
                          'TEST_DEPENDS': 'tests>=1:../../devel/tests',
                          'BOOTSTRAP_DEPENDS': 'bootstrap>=1:../../devel/bootstrap'},
            'devel/generator': {'PKGVERSION': '2', 'BUILD_DEPENDS': 'hostlib>=1:../../devel/hostlib'},
            'devel/library': {}, 'devel/runtime': {}, 'devel/tests': {},
            'devel/bootstrap': {}, 'devel/hostlib': {},
        }
        for package in self.packages:
            directory = self.pkgsrc / package
            directory.mkdir(parents=True)
            (directory / 'Makefile').write_text('# Native metadata fixture\n')
            (directory / 'patches').mkdir()
            (directory / 'patches' / 'patch-one').write_text('patch bytes\n')
        self.config = self.path / 'mk.conf'
        self.config.write_text('# Prepared cross configuration\n')
        self.toolchain = self.path / 'toolchain.json'
        self.toolchain.write_text('{"compiler":"GCC16","revision":"fixture"}\n')
        self.base = self.path / 'base.json'
        self.base.write_text('{"target":"aarch64","revision":"fixture"}\n')
        self.bmake = self.path / 'bmake'
        self.bmake.write_text('#!' + sys.executable + '\n' + r'''
import json, pathlib, sys
args = sys.argv[1:]
directory = pathlib.Path(args[args.index('-C') + 1])
root = directory.parents[1]
settings = dict(arg.split('=', 1) for arg in args if '=' in arg and not arg.startswith('${'))
tracked = settings.get('TEST_PARALLEL') == 'yes'
package = directory.relative_to(root).as_posix()
if tracked:
    events = root / 'events'
    events.mkdir(exist_ok=True)
    pid = str(__import__('os').getpid())
    (events / (pid + '.query.json')).write_text(json.dumps({
        'package': package, 'cross': settings['USE_CROSS_COMPILE'],
        'pattern': settings.get('PKGNAME_REQD')}))
    (events / (pid + '.start')).write_text(str(__import__('time').monotonic_ns()))
    __import__('time').sleep(0.05)
values = json.loads((root / 'metadata.json').read_text())[package]
values = dict(values)
options = values.pop('_options_by_required', {})
if options:
    values['PKG_OPTIONS'] = options.get(settings.get('PKGNAME_REQD'), 'default')
cross = settings['USE_CROSS_COMPILE']
version = values.get('PKGVERSION', '1')
values.setdefault('PKGNAME', directory.name + '-' + version)
values.setdefault('PKGVERSION', version)
values.setdefault('USE_CROSS_COMPILE', cross)
values.setdefault('MACHINE_ARCH', 'aarch64' if cross == 'yes' else 'x86_64')
values.setdefault('MACHINE_GNU_PLATFORM', 'aarch64--netbsd' if cross == 'yes' else 'x86_64--linux')
values.setdefault('.MAKE.MAKEFILES', 'Makefile ../../shared.mk')
values.setdefault('PATCHDIR', 'patches')
values.setdefault('_PATH_ORIG', __import__('os').environ['PATH'])
values.setdefault('PKGSRC_MAKE_ENV', 'MAKECONF=' + settings['MAKECONF'])
values.setdefault('CROSSTARGETSETTINGS', 'TARGET_OPSYS=NetBSD TARGET_MACHINE_ARCH=aarch64')
with (root / 'calls.jsonl').open('a') as stream:
    stream.write(json.dumps({'package': package, 'settings': settings,
                             'targets': [arg for arg in args if arg == 'show-vars']}) + '\n')
if '-dg1' in args:
    print('#*** Global Variables:', file=sys.stderr)
    for name in sorted(values):
        if name.startswith('FILESDIR.'):
            print(name + ' = ' + values[name], file=sys.stderr)
    print('#*** Command-line Variables:', file=sys.stderr)
    if values.get('_inventory_error'):
        print('PRIVATE_VALUE = ' + values['_inventory_error'], file=sys.stderr)
        if tracked:
            (events / (str(__import__('os').getpid()) + '.end')).write_text(str(__import__('time').monotonic_ns()))
        sys.exit(2)
for index, arg in enumerate(args):
    if arg == '-V':
        print(values.get(args[index + 1][2:-1], ''))
if tracked:
    (events / (str(__import__('os').getpid()) + '.end')).write_text(str(__import__('time').monotonic_ns()))
''')
        self.bmake.chmod(0o755)
        self.pkg_admin = self.path / 'pkg_admin'
        self.pkg_admin.write_text('#!' + sys.executable + '\n' + r'''
import sys
assert sys.argv[1] == 'pmatch'
pattern, name = sys.argv[2:]
# Deliberately narrow fixture matcher; production invokes pkg_admin itself.
expected, minimum = pattern.split('>=')
actual, version = name.rsplit('-', 1)
sys.exit(0 if actual == expected and int(version) >= int(minimum) else 1)
''')
        self.pkg_admin.chmod(0o755)
        self.counter = 0

    def run_export(self, *extra, success=True, inventory=True):
        (self.pkgsrc / 'metadata.json').write_text(json.dumps(self.packages))
        self.counter += 1
        output = self.path / ('graph-' + str(self.counter) + '.json')
        requirements = self.path / ('test-requirements-' + str(self.counter) + '.json')
        if '--dependency-phase' in extra and 'build' in extra and inventory:
            extra += ('--test-requirements-output', str(requirements))
        command = [sys.executable, str(SCRIPT), '--sdk-source', self.sdk_source, '--pkgsrc', str(self.pkgsrc),
                   '--makeconf', str(self.config), '--bmake', str(self.bmake),
                   '--pkg-admin', str(self.pkg_admin), '--target', 'aarch64',
                   '--triplet', 'aarch64--netbsd', '--revision', 'fixture',
                   '--toolchain-input', str(self.toolchain), '--base-input', str(self.base),
                   '--root', 'devel/app', '--output', str(output), *extra]
        result = subprocess.run(command, capture_output=True, text=True)
        if success:
            self.assertEqual(result.returncode, 0, result.stderr)
            self.last_inventory = json.loads(requirements.read_text()) if requirements.exists() else None
            if self.last_inventory:
                self.assertEqual(self.last_inventory['graph_sha256'], hashlib.sha256(output.read_bytes()).hexdigest())
            return json.loads(output.read_text())
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(output.exists())
        self.assertFalse(requirements.exists())
        return result.stderr

    def nodes(self, graph):
        return {node['id']: node for node in graph['nodes']}

    def test_runtime_phase_does_not_query_build_only_packages(self):
        # Missing build-tool recipes must not prevent a binary catalog export.
        for package in ('devel/generator', 'devel/library', 'devel/tests', 'devel/bootstrap'):
            self.packages[package]['PKG_FAIL_REASON'] = 'not available on publisher'
        nodes = self.nodes(self.run_export('--dependency-phase', 'runtime'))
        self.assertEqual(set(nodes), {'target:devel/app', 'target:devel/runtime'})
        calls = [json.loads(line) for line in (self.pkgsrc / 'calls.jsonl').read_text().splitlines()]
        self.assertEqual({call['package'] for call in calls}, {'devel/app', 'devel/runtime'})
        self.assertIsNone(self.last_inventory)

    def test_cross_roles_follow_native_installer(self):
        graph = self.run_export()
        nodes = self.nodes(graph)
        generator = next(key for key in nodes if key.startswith('host:devel/generator@'))
        bootstrap = next(key for key in nodes if key.startswith('host:devel/bootstrap@'))
        self.assertEqual(nodes['target:devel/app']['dependencies'], [
            {'id': bootstrap, 'kind': 'tool'},
            {'id': generator, 'kind': 'tool'},
            {'id': 'target:devel/library', 'kind': 'build'},
            {'id': 'target:devel/runtime', 'kind': 'runtime'},
            {'id': 'target:devel/tests', 'kind': 'test'}])
        self.assertEqual(nodes[generator]['dependencies'],
                         [{'id': 'host:devel/hostlib', 'kind': 'build'}])
        calls = [json.loads(line) for line in (self.pkgsrc / 'calls.jsonl').read_text().splitlines()]
        calls = {call['package']: call['settings'] for call in calls}
        self.assertEqual(calls['devel/generator']['USE_CROSS_COMPILE'], 'no')
        self.assertEqual(calls['devel/generator']['TARGET_MACHINE_ARCH'], 'aarch64')
        self.assertNotIn('TARGET_MACHINE_ARCH', calls['devel/hostlib'])
        self.assertEqual(calls['devel/tests']['USE_CROSS_COMPILE'], 'yes')
        self.assertNotIn(str(self.path), json.dumps(graph))

    def test_parallel_jobs_preserve_graph_and_bound_bmake_concurrency(self):
        common = ('--make-variable', 'TEST_PARALLEL=yes')
        serial = self.run_export(*common)
        parallel = self.run_export(*common, '--jobs', '2')
        self.assertEqual(serial, parallel)
        events = self.pkgsrc / 'events'
        intervals = []
        for start in events.glob('*.start'):
            end = events / (start.name[:-6] + '.end')
            self.assertTrue(end.is_file(), f'query process did not finish: {start.name}')
            intervals.extend(((int(start.read_text()), 1), (int(end.read_text()), -1)))
        active = peak = 0
        for _, delta in sorted(intervals):
            active += delta
            peak = max(peak, active)
        self.assertEqual(peak, 2)
        serial = self.run_export(*common, '--dependency-phase', 'build')
        serial_inventory = self.last_inventory
        parallel = self.run_export(*common, '--jobs', '2', '--dependency-phase', 'build')
        self.assertEqual(serial, parallel)
        self.assertEqual(serial_inventory, self.last_inventory)

    def test_parallel_frontier_coalesces_exact_requests(self):
        self.packages['devel/app']['DEPENDS'] = 'library>=1:../../devel/library'
        self.run_export('--jobs', '3')
        calls = [json.loads(line) for line in (self.pkgsrc / 'calls.jsonl').read_text().splitlines()]
        self.assertEqual(sum(call['package'] == 'devel/library' for call in calls), 1)

    def test_metadata_queries_use_pkgsrc_show_vars_target(self):
        self.packages['devel/app']['FILESDIR.extra'] = 'patches'
        self.run_export()
        calls = [json.loads(line) for line in (self.pkgsrc / 'calls.jsonl').read_text().splitlines()]
        app_calls = [call for call in calls if call['package'] == 'devel/app']
        self.assertEqual(len(app_calls), 2)
        self.assertTrue(all(call['targets'] == ['show-vars'] for call in app_calls))

    def test_parallel_frontier_prefetches_new_patterns_for_known_nodes(self):
        self.packages['devel/app']['BUILD_DEPENDS'] = (
            'library>=1:../../devel/library runtime>=1:../../devel/runtime')
        self.packages['devel/runtime']['BUILD_DEPENDS'] = 'library>=2:../../devel/library'
        self.packages['devel/library']['BUILD_DEPENDS'] = 'hostlib>=1:../../devel/hostlib'
        self.packages['devel/library']['PKGVERSION'] = '2'
        options = ('--make-variable', 'TEST_PARALLEL=yes')
        serial = self.run_export('--jobs', '1', *options)
        events = self.pkgsrc / 'events'
        for event in events.iterdir():
            event.unlink()
        parallel = self.run_export('--jobs', '4', *options)
        self.assertEqual(serial, parallel)

        intervals = {}
        for metadata in events.glob('*.query.json'):
            query = json.loads(metadata.read_text())
            if query['cross'] != 'yes':
                continue
            pid = metadata.name[:-len('.query.json')]
            start = int((events / (pid + '.start')).read_text())
            end = int((events / (pid + '.end')).read_text())
            intervals[(query['package'], query['pattern'])] = (start, end)
        variant = intervals[('devel/library', 'library>=2')]
        new_node = intervals[('devel/hostlib', 'hostlib>=1')]
        self.assertLess(max(variant[0], new_node[0]), min(variant[1], new_node[1]))

    def test_parallel_frontier_does_not_prefetch_past_node_limit(self):
        self.run_export('--jobs', '10', '--max-nodes', '1', success=False)
        calls = [json.loads(line) for line in (self.pkgsrc / 'calls.jsonl').read_text().splitlines()]
        self.assertEqual([call['package'] for call in calls], ['devel/app'])

    def test_parallel_frontier_finishes_running_queries_after_failure(self):
        self.packages['devel/library']['_inventory_error'] = 'provider unavailable'
        self.run_export('--jobs', '2', '--make-variable', 'TEST_PARALLEL=yes', success=False)
        events = self.pkgsrc / 'events'
        starts = list(events.glob('*.start'))
        self.assertTrue(starts)
        self.assertTrue(all((events / (start.name[:-6] + '.end')).is_file() for start in starts))

    def test_parallel_frontier_preserves_context_and_variant_refusals(self):
        self.packages['devel/app']['PKGSRC_MAKE_ENV'] = 'CFLAGS=-O0'
        self.assertIn('conflicting recursive contexts', self.run_export(
            '--jobs', '2', '--root', 'devel/library', success=False))
        self.packages['devel/app'].pop('PKGSRC_MAKE_ENV')
        self.packages['devel/tests']['DEPENDS'] = 'library>=0:../../devel/library'
        self.packages['devel/library']['_options_by_required'] = {
            'library>=0': 'debug', 'library>=1': 'normal'}
        self.assertIn('conflicting package variants', self.run_export('--jobs', '2', success=False))

    def test_native_context_stays_host(self):
        graph = self.run_export('--mode', 'native', '--target', 'x86_64', '--triplet', 'x86_64--linux')
        self.assertTrue(all(node['id'].startswith('host:') for node in graph['nodes']))

    def test_explicit_make_variables_reach_every_query_and_are_recorded(self):
        graph = self.run_export('--make-variable', 'EMBERBSD_DARWIN_BOOTSTRAP=yes',
                                '--make-variable', 'EMBERBSD_DARWIN_TOOL_PHASE=initial',
                                '--make-variable', 'PKG_OPTIONS.boost-libs=-icu')
        self.assertIn('make variables: EMBERBSD_DARWIN_BOOTSTRAP=yes, EMBERBSD_DARWIN_TOOL_PHASE=initial, PKG_OPTIONS.boost-libs=-icu',
                      graph['provenance']['source'])
        self.assertIn('make-variables', graph['context']['shared_inputs'])
        calls = [json.loads(line) for line in (self.pkgsrc / 'calls.jsonl').read_text().splitlines()]
        self.assertTrue(calls)
        self.assertTrue(all(call['settings']['EMBERBSD_DARWIN_BOOTSTRAP'] == 'yes' and
                            call['settings']['EMBERBSD_DARWIN_TOOL_PHASE'] == 'initial' and
                            call['settings']['PKG_OPTIONS.boost-libs'] == '-icu'
                            for call in calls))

    def test_make_variable_rejects_flags_reserved_names_and_ambiguous_values(self):
        for assignment in ('PKG_OPTIONS.=-icu', 'PKG_OPTIONS..SHELL=x',
                           'PKG_OPTIONS.boost/libs=-icu', 'PKG_OPTIONS.boost:libs=-icu',
                           'PKG_OPTIONS.boost$libs=-icu', 'MAKEFLAGS=-n', 'MAKECONF=/tmp/other.conf',
                           'USE_CROSS_COMPILE=no', 'TARGET_MACHINE_ARCH=aarch64',
                           'EMBERBSD_DARWIN_BOOTSTRAP=yes;show-vars',
                           'EMBERBSD_DARWIN_BOOTSTRAP=yes extra',
                           'EMBERBSD_DARWIN_BOOTSTRAP='):
            with self.subTest(assignment=assignment):
                self.assertIn('--make-variable assignment', self.run_export(
                    '--make-variable', assignment, success=False))
        self.assertIn('duplicate --make-variable', self.run_export(
            '--make-variable', 'SAMPLE=yes', '--make-variable', 'SAMPLE=no', success=False))

    def test_native_constraint_failure_is_not_resolved_in_python(self):
        self.packages['devel/app']['TOOL_DEPENDS'] = 'generator>=3:../../devel/generator'
        self.assertIn('pkg_admin rejected', self.run_export(success=False))

    def test_target_architecture_mismatch(self):
        self.assertIn('architecture differs', self.run_export('--jobs', '2', '--target', 'amd64', success=False))

    def test_triplet_mismatch(self):
        self.assertIn('triplet differs', self.run_export('--jobs', '2', '--triplet', 'wrong--target', success=False))

    def test_failure_and_skip_reasons_remain_failures(self):
        for key in ('PKG_SKIP_REASON', 'PKG_FAIL_REASON'):
            self.packages['devel/library'][key] = 'provider unavailable'
            self.assertIn('provider unavailable', self.run_export(success=False))
            del self.packages['devel/library'][key]

    def test_shared_include_changes_all_affected_input_hashes(self):
        before = self.nodes(self.run_export())
        (self.pkgsrc / 'shared.mk').write_text('SHARED=changed\n')
        after = self.nodes(self.run_export())
        self.assertTrue(all(before[key]['input_sha256'] != after[key]['input_sha256'] for key in before))

    def test_patch_change_is_local(self):
        before = self.nodes(self.run_export())
        (self.pkgsrc / 'devel/library/patches/patch-one').write_text('repaired\n')
        after = self.nodes(self.run_export())
        self.assertEqual([key for key in before if before[key]['input_sha256'] != after[key]['input_sha256']],
                         ['target:devel/library'])

    def test_failed_inventory_does_not_print_private_values(self):
        self.packages['devel/app']['_inventory_error'] = 'private-makeconf-secret'
        error = self.run_export('--jobs', '2', success=False)
        self.assertIn('variable inventory query failed', error)
        self.assertIn('devel/app (target)', error)
        self.assertNotIn('private-makeconf-secret', error)
        self.assertNotIn('Global Variables', error)
        self.assertNotIn(str(self.config), error)

        del self.packages['devel/app']['_inventory_error']
        self.packages['devel/generator']['_inventory_error'] = 'private-makeconf-secret'
        error = self.run_export('--jobs', '2', success=False)
        self.assertIn('devel/generator (native)', error)
        self.assertNotIn('private-makeconf-secret', error)
        self.assertNotIn('Global Variables', error)
        self.assertNotIn(str(self.config), error)

    def test_vendor_tree_change_only_changes_consumers(self):
        vendor = self.pkgsrc / 'archivers/vendor/files'
        vendor.mkdir(parents=True)
        source = vendor / 'archive.c'
        source.write_text('original source')
        for package in ('devel/library', 'devel/runtime'):
            self.packages[package]['FILESDIR.libarchive'] = '../../archivers/vendor/files'
        before_graph = self.run_export()
        before = self.nodes(before_graph)
        source.write_text('repaired source')
        after_graph = self.run_export()
        after = self.nodes(after_graph)
        self.assertEqual([key for key in before if before[key]['input_sha256'] != after[key]['input_sha256']],
                         ['target:devel/library', 'target:devel/runtime'])
        self.assertEqual(before_graph['context'], after_graph['context'])
        self.assertEqual(set(before), set(after))
        for key in before:
            self.assertEqual(before[key]['dependencies'], after[key]['dependencies'])

    @unittest.skipUnless(os.environ.get('EMBERBSD_BMAKE'), 'set EMBERBSD_BMAKE for native metadata checks')
    def test_real_bmake_ignores_stale_phase_makevars(self):
        package = self.pkgsrc / 'devel/app'
        cache = package / '.stage-install_makevars.mk'
        cache.write_text('_MAKEVARS_MK=defined\nDEPENDS=stale>=1:../../devel/stale\n')
        (package / 'Makefile').write_text(
            '.if !defined(_MAKEVARS_MK)\n.sinclude "' + str(cache) + '"\n.endif\n'
            'PKGNAME=app-1\nPKGVERSION=1\nMACHINE_ARCH=x86_64\n'
            'MACHINE_GNU_PLATFORM=x86_64--linux\n'
            'DEPENDS?=runtime>=1:../../devel/runtime\nall:\n')
        (self.pkgsrc / 'devel/runtime/Makefile').write_text(
            'PKGNAME=runtime-1\nPKGVERSION=1\nMACHINE_ARCH=x86_64\n'
            'MACHINE_GNU_PLATFORM=x86_64--linux\nall:\n')
        graph = self.run_export('--bmake', os.environ['EMBERBSD_BMAKE'], '--mode', 'native',
                                '--target', 'x86_64', '--triplet', 'x86_64--linux',
                                '--dependency-phase', 'runtime')
        nodes = self.nodes(graph)
        self.assertEqual(set(nodes), {'host:devel/app', 'host:devel/runtime'})
        self.assertEqual(nodes['host:devel/app']['dependencies'],
                         [{'id': 'host:devel/runtime', 'kind': 'runtime'}])
        self.assertTrue(cache.is_file())

    @unittest.skipUnless(os.environ.get('EMBERBSD_BMAKE'), 'set EMBERBSD_BMAKE for native metadata checks')
    def test_real_bmake_expands_vendor_tree(self):
        vendor = self.pkgsrc / 'archivers/vendor/files'
        vendor.mkdir(parents=True)
        source = vendor / 'archive.c'
        source.write_text('original source')
        for package in ('devel/app', 'devel/library'):
            text = ('PKGNAME=' + package.split('/')[1] + '-1\n'
                    'PKGVERSION=1\nMACHINE_ARCH=x86_64\n'
                    'MACHINE_GNU_PLATFORM=x86_64--linux\n')
            if package == 'devel/app':
                text += ('VENDOR=../../archivers/vendor\n'
                         '.for component in libarchive\n'
                         'FILESDIR.${component}=${VENDOR}/files\n.endfor\n')
            (self.pkgsrc / package / 'Makefile').write_text(text + 'all:\n')
        args = ('--bmake', os.environ['EMBERBSD_BMAKE'], '--mode', 'native',
                '--target', 'x86_64', '--triplet', 'x86_64--linux', '--root', 'devel/library')
        before = self.nodes(self.run_export(*args))
        source.write_text('repaired source')
        after = self.nodes(self.run_export(*args))
        self.assertEqual([key for key in before if before[key]['input_sha256'] != after[key]['input_sha256']],
                         ['host:devel/app'])

    @unittest.skipUnless(os.environ.get('EMBERBSD_BMAKE') and os.environ.get('EMBERBSD_MAKECONF'),
                         'set EMBERBSD_BMAKE and selected EMBERBSD_MAKECONF for real bmake checks')
    def test_real_selected_bmake_makeconf_uses_explicit_bootstrap_assignment(self):
        package = self.pkgsrc / 'devel/app'
        (package / 'Makefile').write_text(
            '.if ${EMBERBSD_DARWIN_BOOTSTRAP:Uno} != "yes"\n'
            '.error missing explicit bootstrap make variable\n.endif\n'
            'PKGNAME=app-1\nPKGVERSION=1\nMACHINE_ARCH=x86_64\n'
            'MACHINE_GNU_PLATFORM=x86_64--darwin\nall:\n')
        args = ('--bmake', os.environ['EMBERBSD_BMAKE'],
                '--makeconf', os.environ['EMBERBSD_MAKECONF'], '--mode', 'native',
                '--target', 'x86_64', '--triplet', 'x86_64--darwin',
                '--make-variable', 'EMBERBSD_DARWIN_BOOTSTRAP=yes')
        graph = self.run_export(*args)
        self.assertIn('EMBERBSD_DARWIN_BOOTSTRAP=yes', graph['provenance']['source'])

    def test_external_vendor_filename_is_an_input(self):
        vendor = self.path / 'external vendor files'
        vendor.mkdir()
        source = vendor / 'archive.c'
        source.write_text('same bytes')
        self.packages['devel/library']['FILESDIR.vendor'] = str(vendor)
        before = self.nodes(self.run_export())
        source.rename(vendor / 'renamed.c')
        after = self.nodes(self.run_export())
        self.assertEqual([key for key in before if before[key]['input_sha256'] != after[key]['input_sha256']],
                         ['target:devel/library'])

    def test_missing_distinfo_creation_changes_hash(self):
        self.packages['devel/library']['DISTINFO_FILE'] = 'distinfo'
        before = self.nodes(self.run_export())
        (self.pkgsrc / 'devel/library/distinfo').write_text('SHA512 (source) = fixture\n')
        after = self.nodes(self.run_export())
        self.assertNotEqual(before['target:devel/library']['input_sha256'], after['target:devel/library']['input_sha256'])

    def test_base_pin_changes_context(self):
        before = self.run_export()
        self.base.write_text('changed base receipt\n')
        after = self.run_export()
        self.assertNotEqual(before['context']['base_sha256'], after['context']['base_sha256'])

    def test_host_context_variants_have_distinct_ids(self):
        self.packages['devel/generator']['TOOL_DEPENDS'] = 'bootstrap>=1:../../devel/bootstrap'
        nodes = self.nodes(self.run_export())
        variants = [key for key in nodes if key.startswith('host:devel/bootstrap')]
        self.assertEqual(len(variants), 2)
        self.assertIn('host:devel/bootstrap', variants)

    def test_localpatch_change_is_local(self):
        patches = self.path / 'local-patches' / 'devel/library'
        patches.mkdir(parents=True)
        patch = patches / 'patch-local'
        patch.write_text('original local patch')
        self.packages['devel/library']['LOCALPATCHES'] = str(self.path / 'local-patches')
        before = self.nodes(self.run_export())
        patch.write_text('repaired local patch')
        after = self.nodes(self.run_export())
        self.assertEqual([key for key in before if before[key]['input_sha256'] != after[key]['input_sha256']],
                         ['target:devel/library'])

    def test_localpatch_rename_changes_input(self):
        patches = self.path / 'local-patches' / 'devel/library'
        patches.mkdir(parents=True)
        patch = patches / 'patch-a'
        patch.write_text('patch bytes')
        self.packages['devel/library']['LOCALPATCHES'] = str(self.path / 'local-patches')
        before = self.nodes(self.run_export())
        patch.rename(patches / 'patch-z')
        after = self.nodes(self.run_export())
        self.assertNotEqual(before['target:devel/library']['input_sha256'], after['target:devel/library']['input_sha256'])

    def test_cycle_is_rejected_by_sdk(self):
        self.packages['devel/library']['DEPENDS'] = 'app>=1:../../devel/app'
        self.assertIn('cycle', self.run_export(success=False))

    def test_diagnostic_graph_is_written_on_lock_failure(self):
        self.packages['devel/library']['DEPENDS'] = 'app>=1:../../devel/app'
        diagnostic = self.path / 'diagnostic-cycle.json'
        error = self.run_export('--diagnostic-graph', str(diagnostic), success=False)
        self.assertIn('dependency cycle:', error)
        self.assertIn('-[runtime]->', error)
        self.assertTrue(diagnostic.is_file())
        graph = json.loads(diagnostic.read_text())
        self.assertEqual(graph['schema'], 'ports-graph-v1')

    def test_diagnostic_graph_is_not_created_for_valid_graph(self):
        diagnostic = self.path / 'diagnostic-success.json'
        self.run_export('--diagnostic-graph', str(diagnostic))
        self.assertFalse(diagnostic.exists())

    def test_build_phase_separates_perl_gmake_test_cycle(self):
        # Actual pkgsrc relationship: Perl builds with GNU make; GNU make
        # tests with Perl. The test dependency is not a build prerequisite.
        for package in ('lang/perl5', 'devel/gmake'):
            directory = self.pkgsrc / package
            directory.mkdir(parents=True)
            (directory / 'Makefile').write_text('# pkgsrc phase fixture\n')
        self.packages['devel/app']['TOOL_DEPENDS'] = 'perl5>=1:../../lang/perl5'
        self.packages['lang/perl5'] = {'TOOL_DEPENDS': 'gmake>=1:../../devel/gmake'}
        self.packages['devel/gmake'] = {'TEST_DEPENDS': 'perl5>=1:../../lang/perl5'}
        self.assertIn('cycle', self.run_export(success=False))
        nodes = self.nodes(self.run_export('--dependency-phase', 'build'))
        self.assertIn({'id': 'target:devel/runtime', 'kind': 'runtime'},
                      nodes['target:devel/app']['dependencies'])
        self.assertIn('host:devel/gmake', nodes)
        self.assertTrue(any(key.startswith('host:lang/perl5@') for key in nodes))
        self.assertFalse(any(edge['kind'] == 'test' for node in nodes.values()
                             for edge in node['dependencies']))
        self.assertIn({'owner': 'host:devel/gmake', 'role': 'host',
                       'package_path': 'lang/perl5', 'pattern': 'perl5>=1'},
                      self.last_inventory['requirements'])
        self.assertIn({'owner': 'target:devel/app', 'role': 'target',
                       'package_path': 'devel/tests', 'pattern': 'tests>=1'},
                      self.last_inventory['requirements'])
        self.assertEqual(self.last_inventory['status'], 'test-depends-and-tests-pending')

    def test_build_phase_retains_real_build_cycle_guard(self):
        self.packages['devel/library']['DEPENDS'] = 'app>=1:../../devel/app'
        self.assertIn('cycle', self.run_export('--dependency-phase', 'build', success=False))

    def test_dependency_phase_is_a_shared_input(self):
        self.packages['devel/app']['TEST_DEPENDS'] = ''
        all_graph = self.run_export()
        build_graph = self.run_export('--dependency-phase', 'build')
        self.assertEqual(all_graph['nodes'], build_graph['nodes'])
        self.assertNotEqual(all_graph['context']['shared_inputs']['dependency-phase'],
                            build_graph['context']['shared_inputs']['dependency-phase'])
        self.assertIn('build', build_graph['provenance']['source'])

    def test_build_phase_requires_separate_pending_test_inventory(self):
        self.assertIn('requires --test-requirements-output', self.run_export(
            '--dependency-phase', 'build', inventory=False, success=False))

    def test_existing_inventory_is_not_overwritten(self):
        inventory = self.path / 'existing.json'
        inventory.write_text('preserve')
        self.assertIn('must not exist', self.run_export('--dependency-phase', 'build',
            '--test-requirements-output', str(inventory), inventory=False, success=False))
        self.assertEqual(inventory.read_text(), 'preserve')

    def test_recursive_environment_changes_child_inputs(self):
        self.packages['devel/app']['PKGSRC_MAKE_ENV'] = 'CFLAGS=-O0'
        before = self.nodes(self.run_export())
        self.packages['devel/app']['PKGSRC_MAKE_ENV'] = 'CFLAGS=-O2'
        after = self.nodes(self.run_export())
        self.assertNotEqual(before['target:devel/library']['input_sha256'], after['target:devel/library']['input_sha256'])

    def test_file_digest_cache_reuses_unchanged_files_and_rehashes_stat_changes(self):
        spec = importlib.util.spec_from_file_location('export_build_graph', SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        args = types.SimpleNamespace(make_variable=[], pkgsrc=self.pkgsrc,
                                     makeconf=self.config, bmake=self.bmake,
                                     pkg_admin=self.pkg_admin)
        calls = []

        def hash_file(path):
            calls.append(path)
            if path.is_symlink():
                raise OSError('expected a regular file')
            return hashlib.sha256(path.read_bytes()).hexdigest()

        exporter = module.Exporter(args, hash_file)
        path = self.path / 'memoized-input'
        path.write_text('first bytes\n')
        first = exporter.file_digest(path)
        self.assertEqual(exporter.file_digest(path), first)
        self.assertEqual(len(calls), 1)
        path.write_text('changed bytes with a new size\n')
        self.assertNotEqual(exporter.file_digest(path), first)
        self.assertEqual(len(calls), 2)
        target = self.path / 'memoized-target'
        path.rename(target)
        path.symlink_to(target)
        with self.assertRaisesRegex(OSError, 'regular file'):
            exporter.file_digest(path)
        self.assertEqual(len(calls), 3)

    def test_additional_constraint_changes_dependency_key(self):
        self.packages['devel/tests']['DEPENDS'] = 'library>=0:../../devel/library'
        before = self.nodes(self.run_export())
        self.packages['devel/tests']['DEPENDS'] = 'library>=1:../../devel/library'
        after = self.nodes(self.run_export())
        self.assertNotEqual(before['target:devel/library']['input_sha256'], after['target:devel/library']['input_sha256'])

    def test_same_version_different_native_variant_is_rejected(self):
        self.packages['devel/tests']['DEPENDS'] = 'library>=0:../../devel/library'
        self.packages['devel/library']['_options_by_required'] = {
            'library>=0': 'debug', 'library>=1': 'normal'}
        self.assertIn('conflicting package variants', self.run_export(success=False))

    def test_root_and_dependency_variant_is_rejected(self):
        self.packages['devel/library']['_options_by_required'] = {'library>=1': 'normal'}
        self.assertIn('conflicting package variants', self.run_export('--root', 'devel/library', success=False))

    def test_parent_escape_is_refused(self):
        self.packages['devel/app']['DEPENDS'] = 'other>=1:../../../../other'
        self.run_export(success=False)

    def test_closure_limit(self):
        self.assertIn('exceeds --max-nodes', self.run_export('--max-nodes', '2', success=False))


if __name__ == '__main__':
    unittest.main()
