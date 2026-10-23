#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted adapter regressions.
"""Subprocess checks for the native pkgsrc metadata adapter."""
import json
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
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
package = directory.relative_to(root).as_posix()
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
    stream.write(json.dumps({'package': package, 'settings': settings}) + '\n')
if '-dg1' in args:
    print('#*** Global Variables:', file=sys.stderr)
    for name in sorted(values):
        if name.startswith('FILESDIR.'):
            print(name + ' = ' + values[name], file=sys.stderr)
    print('#*** Command-line Variables:', file=sys.stderr)
    if values.get('_inventory_error'):
        print('PRIVATE_VALUE = ' + values['_inventory_error'], file=sys.stderr)
        sys.exit(2)
for index, arg in enumerate(args):
    if arg == '-V':
        print(values.get(args[index + 1][2:-1], ''))
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

    def test_native_context_stays_host(self):
        graph = self.run_export('--mode', 'native', '--target', 'x86_64', '--triplet', 'x86_64--linux')
        self.assertTrue(all(node['id'].startswith('host:') for node in graph['nodes']))

    def test_native_constraint_failure_is_not_resolved_in_python(self):
        self.packages['devel/app']['TOOL_DEPENDS'] = 'generator>=3:../../devel/generator'
        self.assertIn('pkg_admin rejected', self.run_export(success=False))

    def test_target_architecture_mismatch(self):
        self.assertIn('architecture differs', self.run_export('--target', 'amd64', success=False))

    def test_triplet_mismatch(self):
        self.assertIn('triplet differs', self.run_export('--triplet', 'wrong--target', success=False))

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
        error = self.run_export(success=False)
        self.assertIn('variable inventory query failed', error)
        self.assertNotIn('private-makeconf-secret', error)
        self.assertNotIn('Global Variables', error)

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
