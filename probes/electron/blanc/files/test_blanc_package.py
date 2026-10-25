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
BUILD_OPTIONS, remaining = options_parser.parse_known_args()
import sys
sys.argv = [sys.argv[0], *remaining]


class BlancPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sdk_source = BUILD_OPTIONS.sdk_source
        cls.source = Path(BUILD_OPTIONS.source)
        cls.distdir = Path(BUILD_OPTIONS.distdir)
        cls.sdk_root, cls.jsonio, cls.inventory, cls.stream = builder.load_sdk(cls.sdk_source)

    def test_host_node_version_is_exact(self):
        self.assertEqual(builder.HOST_NODE_VERSION, '24.22.1')
        builder.validate_host_node_version(b'v24.22.1\n')
        for value in (b'v24.22.0\n', b'v24.12.0\n', b'v26.0.0\n', b'', b'24.22.1'):
            with self.subTest(value=value), self.assertRaises(builder.BuildError):
                builder.validate_host_node_version(value)

    def test_sdk_api_origin_is_explicit(self):
        source, jsonio, inventory, stream = builder.load_sdk(self.sdk_source)
        self.assertTrue((source / 'src/emberbsd_sdk/__init__.py').is_file())
        self.assertEqual(stream.PRODUCER_STREAM_API, 1)
        self.assertEqual(stream.PRODUCER_INSPECTION_API, 1)

    def test_wrong_sdk_source_is_refused(self):
        with self.assertRaises(builder.BuildError):
            builder.load_sdk('/private/tmp/not-an-emberbsd-sdk')

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
            '44.9.3', '../../devel/electron44',
            'electron>=44.9.3<44.9.4:../../devel/electron44')
        self.assertEqual(path, 'devel/electron44')
        self.assertEqual(dependency, 'electron>=44.9.3<44.9.4:../../devel/electron44')
        for version, package_path, depends in (
            ('44.9.4', '../../devel/electron44', 'electron>=44.9.3<44.9.4:../../devel/electron44'),
            ('44.9.3', '../../www/electron44', 'electron>=44.9.3<44.9.4:../../www/electron44'),
            ('44.9.3', '../../devel/electron44', 'electron>=44.9.2<44.9.4:../../devel/electron44'),
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
                'node_modules/@electron/asar': {'name': '@electron/asar', 'version': '4.3.0'},
            }
            roles = {
                'node_modules/@ghostery/adblocker-electron': {'runtime'},
                'node_modules/@electron/asar': {'build'},
            }
            rows = {
                'node_modules/@ghostery/adblocker-electron': {'name': '@ghostery/adblocker-electron', 'sha512': 'a' * 128, 'sha256': 'a' * 64},
                'node_modules/@electron/asar': {'name': '@electron/asar', 'sha512': 'b' * 128, 'sha256': 'b' * 64},
            }
            metadata = {
                'node_modules/@ghostery/adblocker-electron': {'license': 'MIT'},
                'node_modules/@electron/asar': {'license': 'MIT'},
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
                {'node_modules/@ghostery/adblocker-electron': set(), 'node_modules/@electron/asar': set()},
                rows, metadata, asar, '24.22.1', '44.9.3', '../../devel/electron44',
                'electron>=44.9.3<44.9.4:../../devel/electron44', '4.3.0', 'f' * 64,
                '3.15.0', '1' * 64)
            electron = next(item for item in bom['components'] if item['name'] == 'Electron')
            self.assertEqual(electron['version'], '44.9.3')
            self.assertEqual(electron['scope'], 'required')
            self.assertEqual(electron['properties'][1]['value'], 'false')
            self.assertFalse(any(item.get('bom-ref', '').startswith('pkg:npm/electron@') for item in bom['components']))
            properties = {item['name']: item['value'] for item in bom['metadata']['component']['properties']}
            self.assertEqual(properties['emberbsd:upstreamDevelopmentElectronVersion'], '44.5.1')
            self.assertEqual(properties['emberbsd:upstreamDevelopmentElectronRange'], '^44.5.1')
            self.assertEqual(properties['emberbsd:systemElectron'], '44.9.3')
            asar_tool = next(item for item in bom['components'] if item['name'] == '@electron/asar')
            self.assertEqual(asar_tool['scope'], 'excluded')
            self.assertEqual(bom['metadata']['component']['hashes'][0]['content'], hashlib.sha256(b'fixture ASAR').hexdigest())
            tools = {item['name']: item for item in bom['metadata']['tools']['components']}
            self.assertEqual(tools['CPython']['version'], '3.15.0')
            self.assertEqual(tools['Node.js']['version'], '24.22.1')

    def test_sbom_does_not_misrepresent_electron_as_bundled_npm(self):
        lock_path = self.source / 'package-lock.json'
        with lock_path.open('rb') as stream:
            lock = json.load(stream)
        packages, selected, roles, edges = builder.lock_closure(lock)
        self.assertNotIn('node_modules/electron', selected)
        self.assertIn('node_modules/@electron/asar', selected)
        self.assertEqual(roles['node_modules/@electron/asar'], {'build'})
        # The exact external runtime requirement fails closed before SBOM emission.
        with self.assertRaises(builder.BuildError):
            builder.validate_runtime_dependency(
                '44.9.3', '../../devel/electron44',
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
                    distdir / 'runtime', distdir / 'build', manifest,
                    'f4b8db0e788ff5be1c448440d9c94cd4a543241fa8d8b44d7e10ce2ff0c68462')

    def test_plist_installs_the_generated_compliance_manifest(self):
        plist = (PACKAGE / 'PLIST').read_text(encoding='utf-8')
        self.assertIn('share/doc/blanc/SBOM.json', plist)
        self.assertIn('share/doc/blanc/blueoak-1.0.0.txt', plist)
        makefile = (PACKAGE / 'Makefile').read_text(encoding='utf-8')
        self.assertIn('${FILESDIR:Q}/blueoak-1.0.0.txt', makefile)


if __name__ == '__main__':
    unittest.main()
