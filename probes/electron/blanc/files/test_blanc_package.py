#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted package tests).

import argparse
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import struct
from types import SimpleNamespace
from unittest import mock
import tarfile
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parent
SPEC = importlib.util.spec_from_file_location('blanc_build', HERE / 'build-blanc.py')
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)
options_parser = argparse.ArgumentParser(add_help=False)
options_parser.add_argument('--sdk-source', required=True)
options_parser.add_argument('--source', required=True)
options_parser.add_argument('--distdir', required=True)
options_parser.add_argument('--host-prefix', required=True)
options_parser.add_argument('--node', required=True)
BUILD_OPTIONS, remaining = options_parser.parse_known_args()
import sys
sys.argv = [sys.argv[0], *remaining]


class BlancPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sdk_source = BUILD_OPTIONS.sdk_source
        cls.source = Path(BUILD_OPTIONS.source)
        cls.distdir = Path(BUILD_OPTIONS.distdir)
        cls.sdk_root, cls.jsonio, cls.inventory, cls.stream, cls.native_api = builder.load_sdk(cls.sdk_source)
        cls.native = builder.select_host_tools(cls.native_api, BUILD_OPTIONS.host_prefix, BUILD_OPTIONS.node)

    def test_host_node_version_is_exact(self):
        self.assertEqual(builder.HOST_NODE_VERSION, '26.13.0')
        builder.validate_host_node_version(b'v26.13.0\n')
        for value in (b'v24.22.0\n', b'v24.12.0\n', b'v24.22.1\n', b'', b'26.13.0'):
            with self.subTest(value=value), self.assertRaises(builder.BuildError):
                builder.validate_host_node_version(value)

    def test_sdk_api_origin_is_explicit(self):
        source, jsonio, inventory, stream, native_api = builder.load_sdk(self.sdk_source)
        self.assertTrue((source / 'src/emberbsd_sdk/__init__.py').is_file())
        self.assertEqual(stream.PRODUCER_STREAM_API, 1)
        self.assertEqual(stream.PRODUCER_INSPECTION_API, 1)

    def test_wrong_sdk_source_is_refused(self):
        with self.assertRaises(builder.BuildError):
            builder.load_sdk('/private/tmp/not-an-emberbsd-sdk')

    def native_fixture(self, root):
        # Real native headers from the controller interpreter, not mocked loader
        # results. Node is a selection-only stand-in; no JS execution is claimed.
        binary = root / 'bin'
        binary.mkdir()
        python = binary / 'python3.15'
        node = binary / 'node'
        for path in (python, node):
            shutil.copy2(sys.executable, path)
        return python, node

    def test_native_selection_uses_only_node_and_python(self):
        with tempfile.TemporaryDirectory(prefix='blanc-native-') as temporary:
            root = Path(temporary).resolve()
            python, node = self.native_fixture(root)
            alias = root / 'node-alias'
            alias.symlink_to(node)
            with mock.patch.object(builder.sys, 'executable', str(python)):
                native = builder.select_host_tools(self.native_api, root, alias)
            self.assertEqual(set(native.tools), {'node', 'python'})
            self.assertFalse(native.compiler)
            self.assertEqual(Path(native.tool('node')), node)

    def test_native_selection_rejects_foreign_alias_and_controller(self):
        controller = sys.executable
        with tempfile.TemporaryDirectory(prefix='blanc-native-') as temporary:
            root = Path(temporary).resolve()
            python, node = self.native_fixture(root)
            with mock.patch.object(builder.sys, 'executable', str(python)):
                for alias in (controller, 'node'):
                    with self.subTest(alias=alias), self.assertRaisesRegex(
                            builder.BuildError, 'host-prefix Node'):
                        builder.select_host_tools(self.native_api, root, alias)
            with self.assertRaisesRegex(builder.BuildError, 'host-prefix Python'):
                builder.select_host_tools(self.native_api, root, node)

    def test_native_loader_rejects_missing_escaped_and_foreign_tools(self):
        for fault in ('missing', 'external-link', 'external-interpreter', 'wrong-cpu'):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory(
                    prefix='blanc-native-') as temporary:
                root = Path(temporary).resolve()
                python, node = self.native_fixture(root)
                node.unlink()
                if fault == 'external-link':
                    node.symlink_to(sys.executable)
                elif fault == 'external-interpreter':
                    node.write_text('#!' + sys.executable + '\n')
                    node.chmod(0o755)
                elif fault == 'wrong-cpu':
                    host = self.native_api.platform.system()
                    cpu = self.native_api.platform.machine()
                    if host == 'Darwin':
                        other = 0x01000007 if cpu in ('arm64', 'aarch64') else 0x0100000c
                        node.write_bytes(struct.pack('<8I', 0xfeedfacf, other, 0, 2, 0, 0, 0, 0))
                    else:
                        header = bytearray(python.read_bytes()[:64])
                        self.assertEqual(header[:4], b'\x7fELF')
                        order = '<' if header[5] == 1 else '>'
                        current = struct.unpack_from(order + 'H', header, 18)[0]
                        struct.pack_into(order + 'H', header, 18, 183 if current != 183 else 62)
                        node.write_bytes(header)
                    node.chmod(0o755)
                with mock.patch.object(builder.sys, 'executable', str(python)), \
                        self.assertRaises(builder.BuildError):
                    builder.select_host_tools(self.native_api, root, node)

    def test_child_path_cannot_find_system_shell(self):
        with tempfile.TemporaryDirectory(prefix='blanc-native-') as temporary:
            root = Path(temporary).resolve()
            python, node = self.native_fixture(root)
            with mock.patch.object(builder.sys, 'executable', str(python)):
                native = builder.select_host_tools(self.native_api, root, node)
            env = builder.child_environment(native, root)
            output = builder.run_host_tool(self.stream,
                [sys.executable, '-B', '-I', '-S', '-c',
                 'import shutil; print(shutil.which("sh"))'],
                cwd=root, env=env, timeout=30)
            self.assertEqual(output, b'None\n')
            self.assertNotIn('NODE_OPTIONS', env)
            self.assertNotIn('PYTHONPATH', env)
            self.assertTrue(all(Path(part).is_relative_to(root)
                                for part in env['PATH'].split(builder.os.pathsep)))

    def test_source_copy_uses_only_allowlisted_paths(self):
        with tempfile.TemporaryDirectory(prefix='blanc-allowlist-') as temporary:
            root = Path(temporary) / 'source'
            output = Path(temporary) / 'app'
            (root / 'src').mkdir(parents=True)
            (root / 'src/main.js').write_text('tracked', encoding='utf-8')
            (root / '.env.1password').write_text('must-not-be-read', encoding='utf-8')
            (root / 'untracked.js').write_text('must-not-be-copied', encoding='utf-8')
            copied = builder.copy_allowlist(root, ['src/main.js'], output)
            self.assertEqual(copied, {'src/main.js'})
            self.assertEqual((output / 'src/main.js').read_text(encoding='utf-8'), 'tracked')
            self.assertFalse((output / '.env.1password').exists())
            self.assertFalse((output / 'untracked.js').exists())

    def test_source_copy_rejects_links(self):
        with tempfile.TemporaryDirectory(prefix='blanc-source-link-') as temporary:
            root = Path(temporary) / 'source'
            output = Path(temporary) / 'app'
            root.mkdir()
            (root / 'link.js').symlink_to('/etc/passwd')
            with self.assertRaises((builder.BuildError, OSError)):
                builder.copy_allowlist(root, ['link.js'], output)

    def test_source_archive_extraction_skips_unallowlisted_members(self):
        with tempfile.TemporaryDirectory(prefix='blanc-extract-') as temporary:
            root = Path(temporary)
            archive_path = root / 'source.tar.gz'
            manifest_path = root / 'source-files.json'
            destination = root / 'source'
            manifest = {
                'schemaVersion': 2,
                'upstreamCommit': 'ff55d5948f5c71e802ba2ac464659ef96e055ca9',
                'packageVersion': '1.25.0',
                'applicationFiles': ['src/main.js'],
                'buildInputs': [],
                'generatedFiles': ['test/downstream.test.js'],
            }
            manifest_bytes = json.dumps(manifest, indent=2).encode() + b'\n'
            manifest_path.write_bytes(manifest_bytes)
            with tarfile.open(archive_path, 'w:gz') as archive:
                root_entry = tarfile.TarInfo('blanc-1.25.0/')
                root_entry.type = tarfile.DIRTYPE
                root_entry.mode = 0o755
                archive.addfile(root_entry)
                for name, content in (
                    ('blanc-1.25.0/src/main.js', b'allowed'),
                    ('blanc-1.25.0/.env.1password', b'test sentinel only'),
                    ('blanc-1.25.0/untracked.js', b'not allowed'),
                ):
                    entry = tarfile.TarInfo(name)
                    entry.size = len(content)
                    entry.mode = 0o644
                    entry.mtime = 0
                    archive.addfile(entry, io.BytesIO(content))
            archive_sha = hashlib.sha256(archive_path.read_bytes()).hexdigest()
            manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
            count = builder.extract_source_allowlist(
                self.jsonio, self.inventory, archive_path, destination, manifest_path,
                manifest_sha, archive_sha)
            self.assertEqual(count, 1)
            self.assertEqual((destination / 'src/main.js').read_bytes(), b'allowed')
            self.assertFalse((destination / '.env.1password').exists())
            self.assertFalse((destination / 'untracked.js').exists())
            self.assertFalse((destination / 'test/downstream.test.js').exists())
            bad_destination = root / 'bad-source'
            with self.assertRaises(builder.BuildError):
                builder.extract_source_allowlist(
                    self.jsonio, self.inventory, archive_path, bad_destination, manifest_path,
                    manifest_sha, '0' * 64)
            self.assertFalse(bad_destination.exists())

    def test_exact_runtime_dependency_is_required(self):
        path, dependency = builder.validate_runtime_dependency(
            '45.2.1', '../../devel/electron44',
            'electron>=45.2.1<45.2.2:../../devel/electron44')
        self.assertEqual(path, 'devel/electron44')
        self.assertEqual(dependency, 'electron>=45.2.1<45.2.2:../../devel/electron44')
        for version, package_path, depends in (
            ('45.2.2', '../../devel/electron44', 'electron>=45.2.1<45.2.2:../../devel/electron44'),
            ('45.2.1', '../../www/electron44', 'electron>=45.2.1<45.2.2:../../www/electron44'),
            ('45.2.1', '../../devel/electron44', 'electron>=45.2.0<45.2.2:../../devel/electron44'),
        ):
            with self.subTest(version=version, package_path=package_path, depends=depends):
                with self.assertRaises(builder.BuildError):
                    builder.validate_runtime_dependency(version, package_path, depends)

    def test_recipe_hashes_pin_the_allowlist_and_npm_manifest(self):
        makefile = (PACKAGE / 'Makefile').read_text(encoding='utf-8')
        for name in ('BLANC_SOURCE_FILES_SHA256', 'BLANC_NPM_MANIFEST_SHA256'):
            self.assertIn(name, makefile)
        source_hash = hashlib.sha256((HERE / 'source-files.json').read_bytes()).hexdigest()
        npm_hash = hashlib.sha256((HERE / 'npm-mirror-manifest.json').read_bytes()).hexdigest()
        self.assertIn(source_hash, makefile)
        self.assertIn(npm_hash, makefile)
        self.assertIn('do-extract:', makefile)
        self.assertIn('--sdk-source ${EMBERBSD_SDK_SOURCE:Q} extract', makefile)
        self.assertIn('--source-files-sha256 ${BLANC_SOURCE_FILES_SHA256:Q}', makefile)

    def test_sbom_records_exact_external_runtime_and_build_tools(self):
        with tempfile.TemporaryDirectory(prefix='blanc-sbom-') as temporary:
            asar = Path(temporary) / 'app.asar'
            asar.write_bytes(b'fixture ASAR')
            selected = {
                'node_modules/@ghostery/adblocker-electron': {'name': '@ghostery/adblocker-electron', 'version': '2.18.2'},
            }
            roles = {
                'node_modules/@ghostery/adblocker-electron': {'runtime'},
            }
            rows = {
                'node_modules/@ghostery/adblocker-electron': {'name': '@ghostery/adblocker-electron', 'sha512': 'a' * 128, 'sha256': 'a' * 64},
            }
            metadata = {
                'node_modules/@ghostery/adblocker-electron': {'license': 'MIT'},
            }
            source_manifest = {
                'packageLockSha256': 'c' * 64,
                'upstreamCommit': 'ff55d5948f5c71e802ba2ac464659ef96e055ca9',
                'sourceArchiveSha256': 'd' * 64,
                'allowlistSha256': 'e' * 64,
                'upstreamCommitTimestamp': '2026-10-01T18:41:45-04:00',
            }
            bom = builder.make_sbom(
                source_manifest, {'packages': {
                    '': {'dependencies': {}, 'devDependencies': {'electron': '^44.5.1'}},
                    'node_modules/electron': {'version': '44.5.1'},
                }}, selected, roles,
                {'node_modules/@ghostery/adblocker-electron': set()},
                rows, metadata, asar, '26.13.0', '45.2.1', '../../devel/electron44',
                'electron>=45.2.1<45.2.2:../../devel/electron44',
                {'name': '@electron/asar', 'version': '4.3.1', 'package_path': 'devel/node-electron-asar',
                 'module_path': 'lib/node_modules/@electron/asar', 'license': 'MIT'},
                'f' * 64,
                '3.15.0', '1' * 64)
            electron = next(item for item in bom['components'] if item['name'] == 'Electron')
            self.assertEqual(electron['version'], '45.2.1')
            self.assertEqual(electron['scope'], 'required')
            self.assertEqual(electron['properties'][1]['value'], 'false')
            self.assertFalse(any(item.get('bom-ref', '').startswith('pkg:npm/electron@') for item in bom['components']))
            properties = {item['name']: item['value'] for item in bom['metadata']['component']['properties']}
            self.assertEqual(properties['emberbsd:upstreamDevelopmentElectronVersion'], '44.5.1')
            self.assertEqual(properties['emberbsd:upstreamDevelopmentElectronRange'], '^44.5.1')
            self.assertEqual(properties['emberbsd:systemElectron'], '45.2.1')
            tools = {item['name']: item for item in bom['metadata']['tools']['components']}
            asar_tool = tools['@electron/asar']
            self.assertEqual(asar_tool['scope'], 'excluded')
            self.assertEqual(asar_tool['version'], '4.3.1')
            self.assertEqual(asar_tool['bom-ref'], 'pkgsrc:devel/node-electron-asar@4.3.1')
            self.assertNotIn('hashes', asar_tool)
            asar_properties = {item['name']: item['value'] for item in asar_tool['properties']}
            self.assertEqual(asar_properties['emberbsd:external'], 'true')
            self.assertEqual(asar_properties['emberbsd:pkgsrcPath'], 'devel/node-electron-asar')
            self.assertEqual(bom['metadata']['component']['hashes'][0]['content'], hashlib.sha256(b'fixture ASAR').hexdigest())
            self.assertEqual(tools['CPython']['version'], '3.15.0')
            self.assertEqual(tools['Node.js']['version'], '26.13.0')

    def test_runtime_lock_closure_excludes_external_asar_build_tool(self):
        lock_path = self.source / 'package-lock.json'
        with lock_path.open('rb') as stream:
            lock = json.load(stream)
        packages, selected, roles, edges = builder.lock_closure(lock)
        self.assertNotIn('node_modules/electron', selected)
        self.assertNotIn('node_modules/@electron/asar', selected)
        self.assertTrue(all(role == {'runtime'} for role in roles.values()))
        manifest = json.loads((HERE / 'npm-mirror-manifest.json').read_text())
        self.assertEqual(set(row['lockKey'] for row in manifest['packages']), set(selected))
        self.assertEqual(manifest['hostBuildTool'], {
            'name': '@electron/asar', 'pkgsrcPath': 'devel/node-electron-asar'})
        # The exact external runtime requirement fails closed before SBOM emission.
        with self.assertRaises(builder.BuildError):
            builder.validate_runtime_dependency(
                '45.2.1', '../../devel/electron44',
                'electron>=44.5.1<45:../../devel/electron44')

    def test_modified_npm_archive_is_refused_before_staging(self):
        manifest = HERE / 'npm-mirror-manifest.json'
        with manifest.open('rb') as handle:
            data = json.load(handle)
        first = sorted(data['packages'], key=lambda row: row['lockKey'])[0]
        with tempfile.TemporaryDirectory(prefix='blanc-bad-mirror-') as temporary:
            distdir = Path(temporary)
            corrupt = distdir / first['distfile']
            shutil.copyfile(self.distdir / first['distfile'], corrupt)
            with corrupt.open('ab') as handle:
                handle.write(b'corruption')
            with self.assertRaises(builder.BuildError):
                builder.stage_dependencies(
                    self.jsonio, self.inventory, self.source, distdir,
                    distdir / 'runtime', manifest,
                    hashlib.sha256(manifest.read_bytes()).hexdigest())

    def test_installed_asar_provider_rejects_missing_old_and_outside_prefix(self):
        with tempfile.TemporaryDirectory(prefix='blanc-asar-provider-') as temporary:
            root = Path(temporary) / 'prefix'
            outside = Path(temporary) / 'outside'

            def add_provider(prefix, version='4.3.1'):
                package = prefix / 'lib/node_modules/@electron/asar'
                (package / 'lib').mkdir(parents=True)
                (package / 'package.json').write_text(json.dumps({
                    'name': '@electron/asar', 'version': version, 'type': 'module',
                    'exports': './lib/asar.js', 'license': 'MIT'}))
                (package / 'lib/asar.js').write_text('export {};\n')

            root.mkdir()
            with self.assertRaisesRegex(builder.BuildError, 'missing or outside'):
                builder.resolve_asar_provider(SimpleNamespace(bundle_root=str(root)), self.jsonio, '4.3.1')
            add_provider(root, '4.3.0')
            with self.assertRaisesRegex(builder.BuildError, 'older than required'):
                builder.resolve_asar_provider(SimpleNamespace(bundle_root=str(root)), self.jsonio, '4.3.1')
            shutil.rmtree(root / 'lib/node_modules/@electron/asar')
            outside.mkdir()
            add_provider(outside)
            (root / 'lib/node_modules/@electron').mkdir(parents=True, exist_ok=True)
            (root / 'lib/node_modules/@electron/asar').symlink_to(
                outside / 'lib/node_modules/@electron/asar', target_is_directory=True)
            with self.assertRaisesRegex(builder.BuildError, 'missing or outside'):
                builder.resolve_asar_provider(SimpleNamespace(bundle_root=str(root)), self.jsonio, '4.3.1')

    def test_selected_prefix_asar_pack_list_roundtrip(self):
        provider = builder.resolve_asar_provider(self.native, self.jsonio, '4.3.1')
        self.assertEqual(provider['name'], '@electron/asar')
        self.assertGreaterEqual(tuple(map(int, provider['version'].split('.'))), (4, 3, 1))
        with tempfile.TemporaryDirectory(prefix='blanc-asar-roundtrip-') as temporary:
            work = Path(temporary)
            (work / 'tmp').mkdir()
            (work / 'home').mkdir()
            builder.test_asar_pack_roundtrip(
                self.stream, Path(self.native.tool('node')), HERE / 'asar-pack.mjs',
                provider, self.native, work)

    def test_plist_installs_the_generated_compliance_manifest(self):
        plist = (PACKAGE / 'PLIST').read_text(encoding='utf-8')
        self.assertIn('share/doc/blanc/SBOM.json', plist)
        self.assertIn('share/doc/blanc/blueoak-1.0.0.txt', plist)
        makefile = (PACKAGE / 'Makefile').read_text(encoding='utf-8')
        self.assertIn('${FILESDIR:Q}/blueoak-1.0.0.txt', makefile)


if __name__ == '__main__':
    unittest.main()
