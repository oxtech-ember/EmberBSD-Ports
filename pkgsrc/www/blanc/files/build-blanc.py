#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted package build controller).
"""Build a lockfile-closed Blanc ASAR with the system Electron runtime."""

import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import shutil
import stat
import sys
import tarfile
import platform
import tempfile


MAX_ARCHIVE_BYTES = 512 * 1024 * 1024
MAX_MEMBER_BYTES = 128 * 1024 * 1024
MAX_TOOL_OUTPUT = 8 * 1024 * 1024
NPM_NAME = re.compile(r'^(?:@[a-z0-9._~-]+/)?[a-z0-9._~-]+$')
VERSION = re.compile(r'^[0-9]+\.[0-9]+\.[0-9]+$')
HOST_NODE_VERSION = '26.13.0'
SOURCE_ARCHIVE_SHA256 = 'cdba222bb036eee845716371d7d7aa3f66369bbfd4a40d11951e47d3f6a1f166'


class BuildError(Exception):
    pass


def require(condition, message):
    if not condition:
        raise BuildError(message)


def load_sdk(source):
    root = Path(source)
    require(root.is_absolute(), '--sdk-source must be an absolute path')
    try:
        root = root.resolve(strict=True)
    except OSError as exc:
        raise BuildError(f'cannot resolve SDK source: {exc}') from exc
    source_dir = root / 'src'
    package_dir = source_dir / 'emberbsd_sdk'
    require((package_dir / '__init__.py').is_file(), '--sdk-source has no src/emberbsd_sdk API')
    if str(source_dir) not in sys.path:
        sys.path.insert(0, str(source_dir))
    sdk = importlib.import_module('emberbsd_sdk')
    jsonio = importlib.import_module('emberbsd_sdk.jsonio')
    inventory = importlib.import_module('emberbsd_sdk.inventory')
    stream = importlib.import_module('emberbsd_sdk.stream')
    native = importlib.import_module('emberbsd_sdk.host_prefix')
    for module, relative in (
        (sdk, '__init__.py'),
        (jsonio, 'jsonio.py'),
        (inventory, 'inventory.py'),
        (stream, 'stream.py'),
        (native, 'host_prefix.py'),
    ):
        expected = (package_dir / relative).resolve(strict=True)
        actual = Path(module.__file__).resolve(strict=True)
        require(actual == expected, f'SDK module origin mismatch: {module.__name__}')
    require(getattr(sdk, 'API_VERSION', None) == 1, 'EmberBSD SDK API version 1 is required')
    require(getattr(stream, 'PRODUCER_STREAM_API', None) == 1,
            'EmberBSD SDK producer stream API version 1 is required')
    require(getattr(stream, 'PRODUCER_INSPECTION_API', None) == 1,
            'EmberBSD SDK producer inspection API version 1 is required')
    require(getattr(native, 'HOST_PREFIX_API', None) == 2,
            'EmberBSD SDK host prefix API version 2 is required')
    return root, jsonio, inventory, stream, native


def read_object(jsonio, path, label):
    value = jsonio.read_json(str(path))
    require(isinstance(value, dict), f'{label} must be a JSON object')
    return value


def safe_parts(value):
    require(isinstance(value, str) and value, 'empty file-list path')
    path = PurePosixPath(value)
    require(not path.is_absolute(), f'absolute path in file list: {value}')
    require(str(path) == value and all(part not in ('', '.', '..') for part in path.parts),
            f'unsafe path in file list: {value}')
    require('\\' not in value and '\x00' not in value, f'unsafe path in file list: {value}')
    return path.parts


def checked_source_path(root, relative):
    parts = safe_parts(relative)
    current = root
    for part in parts[:-1]:
        current = current / part
        info = os.lstat(current)
        require(stat.S_ISDIR(info.st_mode), f'non-directory or symlink in source path: {relative}')
    path = current / parts[-1]
    info = os.lstat(path)
    require(stat.S_ISREG(info.st_mode), f'non-regular or symlink source input: {relative}')
    return path


def copy_regular(source, destination):
    info = os.lstat(source)
    require(stat.S_ISREG(info.st_mode), f'expected a regular input file: {source}')
    destination.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(destination, flags, 0o644)
    source_fd = None
    try:
        source_fd = os.open(source, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
        with os.fdopen(fd, 'wb') as output, os.fdopen(source_fd, 'rb') as input_file:
            source_fd = None
            opened = os.fstat(input_file.fileno())
            require((opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns) ==
                    (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns),
                    f'input changed while opening: {source}')
            shutil.copyfileobj(input_file, output, 1024 * 1024)
    except BaseException:
        if source_fd is not None:
            os.close(source_fd)
        try:
            os.unlink(destination)
        except FileNotFoundError:
            pass
        raise


def copy_allowlist(source_root, relative_paths, destination_root):
    """Copy only named upstream files. Never scan the source tree."""
    require(not destination_root.exists(), f'refusing existing output directory: {destination_root}')
    destination_root.mkdir(parents=True)
    seen = set()
    folded = set()
    for relative in relative_paths:
        parts = safe_parts(relative)
        require(relative not in seen, f'duplicate path in source allowlist: {relative}')
        require(relative.casefold() not in folded, f'case-colliding path in source allowlist: {relative}')
        seen.add(relative)
        folded.add(relative.casefold())
        source = checked_source_path(source_root, relative)
        target = destination_root.joinpath(*parts)
        copy_regular(source, target)
    return seen


def resolve_asar_provider(native, jsonio, minimum_version):
    """Select the common @electron/asar module installed in the native prefix."""
    require(VERSION.fullmatch(minimum_version) is not None,
            'invalid minimum @electron/asar version')
    try:
        bundle_root = Path(native.bundle_root).resolve(strict=True)
        package_dir = (bundle_root / 'lib/node_modules/@electron/asar').resolve(strict=True)
        package_dir.relative_to(bundle_root)
    except (OSError, ValueError) as exc:
        raise BuildError(f'@electron/asar provider is missing or outside the selected host prefix: {exc}') from exc
    package_file = package_dir / 'package.json'
    try:
        require(stat.S_ISREG(os.lstat(package_file).st_mode),
                '@electron/asar package.json must be a regular file')
        package_file_target = package_file.resolve(strict=True)
        package_file_target.relative_to(bundle_root)
        require(stat.S_ISREG(package_file_target.stat().st_mode),
                '@electron/asar package.json target must be a regular file')
        metadata = read_object(jsonio, package_file_target, '@electron/asar package metadata')
    except (OSError, ValueError) as exc:
        raise BuildError(f'@electron/asar metadata escapes the selected host prefix: {exc}') from exc
    require(metadata.get('name') == '@electron/asar',
            'selected host-prefix ASAR package has the wrong name')
    version = metadata.get('version', '')
    require(VERSION.fullmatch(version) is not None,
            'selected host-prefix ASAR package has an invalid version')
    require(tuple(map(int, version.split('.'))) >= tuple(map(int, minimum_version.split('.'))),
            f'host-prefix @electron/asar {version} is older than required {minimum_version}')
    require(metadata.get('type') == 'module',
            'host-prefix @electron/asar does not expose the supported ES module API')
    entry = package_dir / 'lib/asar.js'
    try:
        entry_target = entry.resolve(strict=True)
        entry_target.relative_to(bundle_root)
        require(stat.S_ISREG(entry_target.stat().st_mode),
                '@electron/asar API entry target must be a regular file')
    except (OSError, ValueError) as exc:
        raise BuildError(f'@electron/asar API entry is missing or outside the selected host prefix: {exc}') from exc
    return {'name': metadata['name'], 'version': version, 'package_path': 'devel/node-electron-asar',
            'module_path': 'lib/node_modules/@electron/asar', 'entry': str(entry_target),
            'license': package_license(metadata)}


def test_asar_pack_roundtrip(stream, node, wrapper, asar_tool, native, work):
    """Exercise the selected provider's real createPackage/listPackage API."""
    env = child_environment(native, work)
    with tempfile.TemporaryDirectory(prefix='blanc-asar-api-', dir=work / 'tmp') as temporary:
        root = Path(temporary)
        app = root / 'app'
        app.mkdir()
        (app / 'probe.txt').write_text('Blanc ASAR API roundtrip\n', encoding='utf-8')
        output = root / 'probe.asar'
        result = run_host_tool(stream, [str(node), str(wrapper), asar_tool['entry'], str(app), str(output)],
                               cwd=work, env=env, timeout=60)
        packed = json.loads(result)
        require(output.is_file() and 'probe.txt' in packed.get('files', []),
                'selected @electron/asar provider failed createPackage/listPackage roundtrip')


def digest_file(inventory, path, algorithm):
    return inventory.hash_file(str(path), algorithm)


def copy_module_tree(source, destination):
    require(not destination.exists(), f'refusing existing module tree: {destination}')
    destination.mkdir(parents=True)
    for current, dirs, files in os.walk(source, topdown=True, followlinks=False):
        dirs.sort()
        files.sort()
        relative = Path(current).relative_to(source)
        out_dir = destination / relative
        out_dir.mkdir(parents=True, exist_ok=True)
        for name in dirs:
            path = Path(current) / name
            require(stat.S_ISDIR(os.lstat(path).st_mode), f'link or special module directory: {path}')
        for name in files:
            path = Path(current) / name
            require(stat.S_ISREG(os.lstat(path).st_mode), f'link or special module file: {path}')
            copy_regular(path, out_dir / name)


def consume_bounded(reader):
    data = bytearray()
    while chunk := reader.read(1024 * 1024):
        data.extend(chunk)
        require(len(data) <= MAX_TOOL_OUTPUT, 'host tool produced excessive stdout')
    return bytes(data)


def select_host_tools(native_api, prefix, node):
    require(Path(prefix).is_absolute(), '--host-prefix must be an absolute path')
    try:
        native = native_api.load_host_prefix(prefix, required_roles=('node', 'python'))
    except native_api.SDKError as exc:
        raise BuildError(str(exc)) from exc
    require(Path(node).is_absolute() and
            Path(node).resolve(strict=True) == Path(native.tool('node')).resolve(strict=True),
            '--node must select the host-prefix Node.js')
    require(Path(sys.executable).resolve(strict=True) ==
            Path(native.tool('python')).resolve(strict=True),
            'Run build and test with the selected host-prefix Python')
    return native


def child_environment(native, work, node_path=None):
    env = {
        'PATH': native.path,
        'HOME': str(work / 'home'),
        'LANG': 'C',
        'LC_ALL': 'C',
        'TZ': 'UTC',
        'TMPDIR': str(work / 'tmp'),
        'CI': '1',
        'NO_COLOR': '1',
    }
    if node_path is not None:
        env['NODE_PATH'] = node_path
    return env


def run_host_tool(stream, argv, *, cwd, env, timeout=900):
    result = stream.run_streamed(argv, consume_bounded, cwd=str(cwd), env=env,
                                 stderr_limit=1024 * 1024, timeout=timeout)
    if result.stderr:
        sys.stderr.buffer.write(result.stderr)
    require(not result.stderr_truncated, 'host tool stderr exceeded the inspection limit')
    return result.value


def next_patch(version):
    match = VERSION.fullmatch(version)
    require(match is not None, f'invalid Electron version: {version}')
    major, minor, patch = map(int, version.split('.'))
    return f'{major}.{minor}.{patch + 1}'


def validate_host_node_version(output):
    require(output.decode('ascii').strip() == 'v' + HOST_NODE_VERSION,
            f'Blanc package tools require the selected host Node.js {HOST_NODE_VERSION}')


def validate_runtime_dependency(version, package_path, dependency):
    expected_path = posixpath.normpath(posixpath.join('www/blanc', package_path))
    require(expected_path == 'devel/electron44',
            f'Electron package path does not resolve from www/blanc: {package_path}')
    expected = f'electron>={version}nb2<{next_patch(version)}:{package_path}'
    require(dependency == expected,
            f'SBOM runtime version and pkgsrc dependency disagree: expected {expected}')
    require(version == '45.2.1', 'Blanc package is qualified only for Electron 45.2.1')
    return expected_path, expected


def package_license(metadata):
    value = metadata.get('license')
    if value is None:
        return 'NOASSERTION'
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def project_runtime(stream, jsonio, native, work, projection_path, electron_version, runtime_root):
    """Copy the already installed common runtime after the shared owner verifies it."""
    projection = Path(projection_path).resolve(strict=True)
    prefix = Path(native.bundle_root).resolve(strict=True)
    pkg_admin = (prefix / 'sbin/pkg_admin').resolve(strict=True)
    require(pkg_admin.is_relative_to(prefix) and pkg_admin.is_file(),
            'pkg_admin must belong to the selected native prefix')
    from emberbsd_sdk import host_prefix
    try:
        host_prefix.validate_host_executable(str(prefix), str(pkg_admin), native.host, search_path=native.path)
    except host_prefix.SDKError as exc:
        raise BuildError(str(exc)) from exc
    roots = ('@ghostery/adblocker-electron=devel/node-ghostery-adblocker-electron',
             '@mozilla/readability=devel/node-readability', 'dompurify=devel/node-dompurify')
    command = [str(native.tool('python')), '-B', '-I', '-S', str(projection),
               '--prefix', str(prefix), '--node', str(native.tool('node')),
               '--pkg-admin', str(pkg_admin), '--runtime', 'electron=' + electron_version]
    for root in roots:
        command += ['--root', root]
    result = jsonio.loads_json(run_host_tool(stream, command, cwd=work,
                                               env=child_environment(native, work)))
    require(isinstance(result, dict) and result.get('schemaVersion') == 1 and
            isinstance(result.get('modules'), list), 'invalid common JS projection result')
    rows = result['modules']
    require(rows and len({row['name'] for row in rows}) == len(rows), 'invalid projected module names')
    runtime_root.mkdir(parents=True)
    for row in rows:
        name = row['name']
        require(NPM_NAME.fullmatch(name) and row['modulePath'] == 'lib/node_modules/' + name,
                'invalid projected module path')
        source = prefix / row['modulePath']
        copy_module_tree(source, runtime_root / name)
    return rows


def make_projected_sbom(source_manifest, lock, rows, app_asar, node_version,
                        electron_version, electron_pkgpath, electron_dependency,
                        asar_tool, node_sha256, python_version, python_sha256):
    runtime_path, dependency = validate_runtime_dependency(electron_version, electron_pkgpath, electron_dependency)
    root_ref = 'pkg:generic/ember-browser@1.46.0'
    electron_ref = f'pkgsrc:{runtime_path}@{electron_version}'
    refs = {row['name']: f"pkgsrc:{row['pkgpath']}@{row['version']}" for row in rows}
    components = [{'type': 'framework', 'bom-ref': electron_ref, 'name': 'Electron',
                   'version': electron_version, 'scope': 'required', 'properties': [
                       {'name': 'emberbsd:pkgsrcPath', 'value': runtime_path},
                       {'name': 'emberbsd:dependency', 'value': dependency},
                       {'name': 'emberbsd:bundled', 'value': 'false'}]}]
    dependencies = [{'ref': electron_ref, 'dependsOn': []}]
    for row in rows:
        properties = [{'name': 'emberbsd:pkgsrcPath', 'value': row['pkgpath']},
                      {'name': 'emberbsd:packageName', 'value': row['pkgname']},
                      {'name': 'emberbsd:distinfoSha256', 'value': row['distinfoSha256']},
                      {'name': 'emberbsd:buildVersionSha256', 'value': row['buildVersionSha256']}]
        component = {'type': 'library', 'bom-ref': refs[row['name']], 'name': row['name'],
                     'version': row['version'], 'scope': 'required', 'properties': properties}
        if isinstance(row['license'], str) and row['license'] != 'NOASSERTION':
            component['licenses'] = [{'license': {'name': row['license']}}]
        components.append(component)
        children = set(row['dependencies']) | set(row['peers'])
        require(children <= set(refs) | {'electron'}, 'unknown projected SBOM dependency')
        dependencies.append({'ref': refs[row['name']], 'dependsOn': sorted(
            electron_ref if name == 'electron' else refs[name] for name in children)})
    root_names = ('@ghostery/adblocker-electron', '@mozilla/readability', 'dompurify')
    require(all(name in refs for name in root_names), 'missing projected SBOM root')
    dependencies.insert(0, {'ref': root_ref, 'dependsOn': [electron_ref] + [refs[name] for name in root_names]})
    root = {'type': 'application', 'bom-ref': root_ref, 'name': 'Ember Browser', 'version': '1.46.0',
            'licenses': [{'license': {'id': 'MIT'}}],
            'hashes': [{'alg': 'SHA-256', 'content': hashlib.sha256(app_asar.read_bytes()).hexdigest()}],
            'properties': [{'name': 'emberbsd:pkgsrcPackage', 'value': 'ember-browser-1.46.0nb1'},
                           {'name': 'emberbsd:upstreamName', 'value': 'Blanc'},
                           {'name': 'emberbsd:upstreamVersion', 'value': '1.46.0'},
                           {'name': 'emberbsd:upstreamCommit', 'value': source_manifest['upstreamCommit']},
                           {'name': 'emberbsd:sourceArchiveSha256', 'value': source_manifest['sourceArchiveSha256']},
                           {'name': 'emberbsd:packageLockSha256', 'value': source_manifest['packageLockSha256']},
                           {'name': 'emberbsd:sourceFileAllowlistSha256', 'value': source_manifest['allowlistSha256']}]}
    tools = [{'type': 'application', 'name': 'CPython', 'version': python_version,
              'hashes': [{'alg': 'SHA-256', 'content': python_sha256}]},
             {'type': 'application', 'name': 'Node.js', 'version': node_version,
              'hashes': [{'alg': 'SHA-256', 'content': node_sha256}]},
             {'type': 'library', 'name': asar_tool['name'], 'version': asar_tool['version']}]
    return {'bomFormat': 'CycloneDX', 'specVersion': '1.5', 'version': 1,
            'metadata': {'timestamp': source_manifest['upstreamCommitTimestamp'], 'component': root,
                         'tools': {'components': tools}},
            'components': components, 'dependencies': dependencies}


def check_source_files(jsonio, inventory, source_root, manifest_path, expected_sha):
    actual_sha = digest_file(inventory, manifest_path, 'sha256')
    require(actual_sha == expected_sha, 'upstream source allowlist does not match the recipe checksum')
    source_manifest = read_object(jsonio, manifest_path, 'upstream source allowlist')
    require(source_manifest.get('schemaVersion') == 2 and
            source_manifest.get('upstreamCommit') == '6479ed3a314e4fd6219b8de1598bacffa78b4d7c' and
            source_manifest.get('packageVersion') == '1.46.0',
            'upstream source allowlist provenance mismatch')
    app_paths = source_manifest.get('applicationFiles')
    build_paths = source_manifest.get('buildInputs')
    generated_paths = source_manifest.get('generatedFiles')
    require(isinstance(app_paths, list) and isinstance(build_paths, list) and
            isinstance(generated_paths, list),
            'upstream source allowlist is incomplete')
    require(len(set(app_paths)) == len(app_paths) and len(set(build_paths)) == len(build_paths) and
            len(set(generated_paths)) == len(generated_paths) and
            not (set(generated_paths) & (set(app_paths) | set(build_paths))),
            'upstream source allowlist contains duplicate paths')
    for path in app_paths + build_paths + generated_paths:
        checked_source_path(source_root, path)
    lock_sha = digest_file(inventory, source_root / 'package-lock.json', 'sha256')
    require(source_manifest.get('packageLockSha256') == lock_sha,
            'source allowlist package-lock checksum mismatch')
    source_manifest['allowlistSha256'] = actual_sha
    return source_manifest


def extract_source_allowlist(jsonio, inventory, archive_path, destination, manifest_path,
                             expected_manifest_sha, expected_archive_sha):
    """Extract only named source inputs. Skip every other upstream archive member."""
    require(re.fullmatch(r'[0-9a-f]{64}', expected_archive_sha) is not None,
            'invalid pinned Blanc source archive checksum')
    require(digest_file(inventory, archive_path, 'sha256') == expected_archive_sha,
            'Blanc source distfile checksum differs from the v1.46.0 release archive')
    manifest_sha = digest_file(inventory, manifest_path, 'sha256')
    require(manifest_sha == expected_manifest_sha,
            'upstream source allowlist does not match the recipe checksum')
    manifest = read_object(jsonio, manifest_path, 'upstream source allowlist')
    require(manifest.get('schemaVersion') == 2 and
            manifest.get('upstreamCommit') == '6479ed3a314e4fd6219b8de1598bacffa78b4d7c' and
            manifest.get('packageVersion') == '1.46.0',
            'upstream source allowlist provenance mismatch')
    app_paths = manifest.get('applicationFiles')
    build_paths = manifest.get('buildInputs')
    generated_paths = manifest.get('generatedFiles')
    require(isinstance(app_paths, list) and isinstance(build_paths, list) and
            isinstance(generated_paths, list), 'upstream source allowlist is incomplete')
    upstream_paths = app_paths + build_paths
    require(len(set(app_paths)) == len(app_paths) and len(set(build_paths)) == len(build_paths) and
            len(set(generated_paths)) == len(generated_paths) and
            not (set(generated_paths) & set(upstream_paths)),
            'upstream source allowlist contains duplicate paths')
    expected = set()
    for relative in upstream_paths + generated_paths:
        parts = safe_parts(relative)
        require('.env.1password' not in parts, 'secret filename in source allowlist')
        if relative in upstream_paths:
            expected.add(relative)
    require(not destination.exists(), f'refusing existing extracted source: {destination}')
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.mkdir(mode=0o755)
    archive_prefix = 'blanc-1.46.0/'
    found = set()
    try:
        with tarfile.open(archive_path, mode='r|gz') as archive:
            for member in archive:
                name = member.name
                if name.rstrip('/') == archive_prefix.rstrip('/'):
                    require(member.isdir(), 'Blanc source archive root is not a directory')
                    continue
                require(name.startswith(archive_prefix), 'unexpected root in Blanc source archive')
                relative = name[len(archive_prefix):].rstrip('/')
                if not relative:
                    continue
                safe_parts(relative)
                if relative not in expected:
                    continue
                require(member.isreg(), f'non-regular allowlisted source input: {relative}')
                require(relative not in found, f'duplicate allowlisted source input: {relative}')
                require(0 <= member.size <= MAX_MEMBER_BYTES,
                        f'oversized allowlisted source input: {relative}')
                target = destination.joinpath(*safe_parts(relative))
                target.parent.mkdir(parents=True, exist_ok=True)
                source = archive.extractfile(member)
                require(source is not None, f'cannot read allowlisted source input: {relative}')
                size = 0
                with source, target.open('xb') as output:
                    while chunk := source.read(1024 * 1024):
                        size += len(chunk)
                        require(size <= member.size, f'oversized source member: {relative}')
                        output.write(chunk)
                require(size == member.size, f'truncated source member: {relative}')
                os.chmod(target, member.mode & 0o777)
                found.add(relative)
        require(found == expected,
                f'Blanc source archive is missing allowlisted files: {sorted(expected - found)}')
    except BaseException:
        shutil.rmtree(destination)
        raise
    return len(found)


RESERVED_COLORWAYS = frozenset(('sunrise', 'sunrise-dark', 'paper', 'ink', 'graphite',
                                'default', 'midnight', 'cream', 'forest', 'sage', 'ember', 'plum', 'gold'))


def reserved_artwork(path):
    path = PurePosixPath(path)
    if str(path) == 'src/renderer/sunrise-hero-mark.png':
        return True
    if str(path.parent) != 'src/renderer/pages':
        return False
    name = path.name
    return (name in ('icon.svg', 'sunrise-mark.png', 'sunrise-favicon-mark.png', 'mahjong-dragon-white.png') or
            name.startswith('icon-sunrise') and name.endswith('.png') or
            name.startswith('icon-') and name.endswith('.png') and name[5:-4] in RESERVED_COLORWAYS)


def validate_derivative_asar(packed):
    """Check identity and security inputs read from the actual ASAR."""
    metadata = packed.get('packageMetadata')
    require(isinstance(metadata, dict) and metadata.get('name') == 'ember-browser' and
            metadata.get('productName') == 'Ember Browser' and
            metadata.get('build', {}).get('appId') == 'org.emberbsd.browser',
            'ASAR package identity does not match Ember Browser')
    require("org.emberbsd.browser" in packed.get('identitySource', ''),
            'ASAR runtime identity does not match the package')
    require("path.join(app.getPath('appData'), 'Bowser')" not in packed.get('mainSource', ''),
            'ASAR must not migrate the upstream profile')
    tab_source = packed.get('tabSource', '')
    for policy in ('contextIsolation: true', 'nodeIntegration: false', 'sandbox: true'):
        require(policy in tab_source, f'ASAR tab policy is missing {policy}')
    contents = packed.get('files')
    require(isinstance(contents, list), 'ASAR packer returned no file list')
    for name in contents:
        require(not reserved_artwork(name), f'ASAR contains reserved upstream artwork: {name}')
    require('src/renderer/pages/ember-browser.svg' in contents,
            'ASAR is missing the derivative icon')
    require('src/renderer/pages/ember-browser.png' in contents,
            'ASAR is missing the derivative native icon')
    for notice in ('LICENSE', 'ASSET-LICENSE.md', 'THIRD-PARTY-NOTICES.md', 'TRADEMARKS.md'):
        require(notice in contents, f'ASAR is missing upstream notice: {notice}')
    return contents


def run_node_tests(stream, source_root, native, work):
    test_paths = [
        'test/unit/document-policy.test.js',
        'test/unit/updater-policy.test.js',
        'test/unit/display-capture-netbsd.test.js',
        'test/unit/display-capture-packaged-lock.test.js',
        'test/unit/display-capture-platform-lock.test.js',
    ]
    output = run_host_tool(stream, [native.tool('node'), '--test', *(str(source_root / p) for p in test_paths)], cwd=source_root,
                           env=child_environment(native, work), timeout=300)
    sys.stdout.buffer.write(output)
    env = child_environment(native, work)
    env['EMBER_BROWSER_SOURCE'] = str(source_root)
    for filename in ('test-netbsd-system-updater.cjs', 'test-netbsd-telemetry.cjs'):
        output = run_host_tool(stream, [native.tool('node'), str(Path(__file__).parent / filename)],
                               cwd=source_root, env=env, timeout=300)
        sys.stdout.buffer.write(output)


def run_python_tests(stream, source_root, dist_dir, native, work, sdk_root):
    test_path = Path(__file__).parent / 'test_blanc_package.py'
    output = run_host_tool(stream, [native.tool('python'), '-B', '-I', '-S', str(test_path),
                                    '--sdk-source', str(sdk_root), '--source', str(source_root),
                                    '--distdir', str(dist_dir), '--host-prefix', native.bundle_root,
                                    '--node', native.tool('node')],
                           cwd=source_root, env=child_environment(native, work), timeout=300)
    sys.stdout.buffer.write(output)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk-source', required=True)
    parser.add_argument('action', choices=('build', 'test', 'extract'))
    parser.add_argument('--source', required=True)
    parser.add_argument('--archive')
    parser.add_argument('--distdir')
    parser.add_argument('--work')
    parser.add_argument('--node')
    parser.add_argument('--host-prefix')
    parser.add_argument('--asar-min-version')
    parser.add_argument('--source-archive-sha256')
    parser.add_argument('--source-files-sha256')
    parser.add_argument('--projection')
    parser.add_argument('--electron-version')
    parser.add_argument('--electron-package-path')
    parser.add_argument('--electron-depends')
    return parser.parse_args()


def main():
    args = parse_args()
    sdk_root, jsonio, inventory, stream, native_api = load_sdk(args.sdk_source)
    require(sys.version_info >= (3, 15), 'Blanc package tools require host Python 3.15 or newer')
    require(args.source_archive_sha256 == SOURCE_ARCHIVE_SHA256,
            'Blanc source distfile checksum differs from the v1.46.0 release archive')
    source_list_path = Path(__file__).parent / 'source-files.json'
    if args.action == 'extract':
        require(args.archive and args.source_archive_sha256 and args.source_files_sha256,
                'extract requires --archive and both pinned SHA-256 values')
        destination = Path(args.source).resolve(strict=False)
        archive_path = Path(args.archive).resolve(strict=True)
        count = extract_source_allowlist(
            jsonio, inventory, archive_path, destination, source_list_path,
            args.source_files_sha256, args.source_archive_sha256)
        print(f'Extracted {count} allowlisted Blanc source files.')
        return 0
    require(args.distdir and args.work and args.node and args.host_prefix and args.asar_min_version and
            args.source_archive_sha256 and
            args.source_files_sha256 and args.projection and args.electron_version and args.electron_package_path and
            args.electron_depends, 'build and test require all pinned host, source, and runtime arguments')
    native = select_host_tools(native_api, args.host_prefix, args.node)
    asar_tool = resolve_asar_provider(native, jsonio, args.asar_min_version)
    source_root = Path(args.source).resolve(strict=True)
    dist_dir = Path(args.distdir).resolve(strict=True)
    work = Path(args.work).resolve(strict=True)
    (work / 'tmp').mkdir(exist_ok=True)
    (work / 'home').mkdir(exist_ok=True)
    node = Path(native.tool('node'))
    env = child_environment(native, work)
    node_version = run_host_tool(stream, [str(node), '--version'], cwd=work, env=env, timeout=30)
    validate_host_node_version(node_version)
    source_manifest = check_source_files(
        jsonio, inventory, source_root, source_list_path,
        args.source_files_sha256)
    source_manifest['sourceArchiveSha256'] = args.source_archive_sha256
    validate_runtime_dependency(args.electron_version, args.electron_package_path, args.electron_depends)
    if args.action == 'test':
        run_node_tests(stream, source_root, native, work)
        test_asar_pack_roundtrip(
            stream, node, Path(__file__).parent / 'asar-pack.mjs', asar_tool, native, work)
        run_python_tests(stream, source_root, dist_dir, native, work, sdk_root)
        return 0

    runtime_root = work / 'runtime-node-modules'
    app_root = work / 'app-stage'
    seed_root = work / 'seed-inputs'
    asar_path = work / 'app.asar'
    sbom_path = work / 'SBOM.json'
    runtime_providers = project_runtime(stream, jsonio, native, work, args.projection,
                                        args.electron_version, runtime_root)
    lock = read_object(jsonio, source_root / 'package-lock.json', 'upstream lockfile')
    require(not app_root.exists() and not seed_root.exists() and not asar_path.exists() and not sbom_path.exists(),
            'refusing to overwrite existing Blanc build output')
    copy_allowlist(source_root, source_manifest['applicationFiles'], app_root)
    # Replace upstream identity assets only after validating and copying the
    # original source allowlist. Keep the upstream licence notices in the ASAR.
    pages = app_root / 'src/renderer/pages'
    for relative in source_manifest['applicationFiles']:
        if reserved_artwork(relative):
            (app_root / relative).unlink()
    copy_regular(Path(__file__).parent / 'ember-browser.svg', pages / 'ember-browser.svg')
    copy_regular(Path(__file__).parent / 'ember-browser.png', pages / 'ember-browser.png')
    copy_regular(Path(__file__).parent / 'netbsd-system-updater.js', app_root / 'src/main/netbsd-system-updater.js')
    copy_module_tree(runtime_root, app_root / 'node_modules')
    copy_allowlist(source_root, source_manifest['buildInputs'] + source_manifest['generatedFiles'], seed_root)
    # Generate only the consumer-facing desktop catalogs from upstream messages.
    copy_regular(source_root / 'src/renderer/pages/i18n.js', seed_root / 'src/renderer/pages/i18n.js')
    run_host_tool(stream, [str(node), str(Path(__file__).parent / 'rebrand-i18n.mjs'),
                           str(seed_root), str(Path(__file__).parent / 'rebrand-i18n-keys.json')],
                  cwd=seed_root, env=env, timeout=300)
    generated_catalogs = [f'src/renderer/pages/strings.{locale}.js'
                          for locale in ('en', 'en-XA', 'de', 'es', 'fr', 'it', 'pt-BR')]
    generated_catalogs += ['src/main/i18n-locales.json', 'src/main/ublock-strings.json']
    for relative in generated_catalogs:
        target = app_root / relative
        target.unlink()
        copy_regular(seed_root / relative, target)
    resource_provider = next((row for row in runtime_providers
                              if row['pkgpath'] == 'devel/node-ghostery-adblocker'), None)
    require(resource_provider is not None, 'missing common Ghostery resource provider')
    prefix = Path(native.bundle_root).resolve(strict=True)
    resource = prefix / 'share/ghostery-adblocker/resources.json'
    contents_path = prefix / 'pkgdb' / resource_provider['pkgname'] / '+CONTENTS'
    require('share/ghostery-adblocker/resources.json' in contents_path.read_text().splitlines(),
            'Ghostery resources are not owned by the selected provider')
    require(resource.is_file() and not resource.is_symlink() and resource.resolve(strict=True).is_relative_to(prefix),
            'invalid common Ghostery resource path')
    pin = read_object(jsonio, seed_root / 'adblock/sources/pinned.json', 'Ghostery source pin')
    require(digest_file(inventory, resource, 'sha256') == pin['ghosteryResources']['sha256'],
            'common Ghostery resource differs from the source pin')
    for target in (seed_root / 'adblock/sources/ghostery-resources.json',
                   app_root / 'adblock/sources/ghostery-resources.json'):
        target.unlink()
        copy_regular(resource, target)
    shim = work / 'electron-shim'
    shim.mkdir()
    (shim / 'electron.js').write_text('module.exports = Object.create(null);\n', encoding='utf-8')
    seed_env = child_environment(native, work, node_path=str(shim) + os.pathsep + str(runtime_root))
    run_host_tool(stream, [str(node), str(seed_root / 'adblock/seed.mjs'), '--prepare'],
                  cwd=seed_root, env=seed_env, timeout=900)
    generated_seed = seed_root / 'src/main/assets/adblock-engine-seed.bin'
    require(generated_seed.is_file(), 'upstream adblock seed builder produced no binary')
    copy_regular(generated_seed, app_root / 'src/main/assets/adblock-engine-seed.bin')
    require((app_root / 'node_modules/electron').exists() is False,
            'the Electron runtime must remain external')
    require((app_root / 'node_modules/@electron/asar').exists() is False,
            'the ASAR build tool must remain outside the application')
    asar_api = Path(asar_tool['entry'])
    asar_wrapper = Path(__file__).parent / 'asar-pack.mjs'
    asar_output = run_host_tool(stream, [str(node), str(asar_wrapper), str(asar_api), str(app_root), str(asar_path)],
                                cwd=work, env=env, timeout=900)
    packed = jsonio.loads_json(asar_output)
    require(isinstance(packed, dict), 'ASAR packer result must be a JSON object')
    contents = validate_derivative_asar(packed)
    for relative in (
        'package.json', 'src/main/main.js', 'src/main/assets/adblock-engine-seed.bin',
        'node_modules/@ghostery/adblocker-electron/package.json',
    ):
        require(relative in contents, f'ASAR is missing required application input: {relative}')
    require(not any(name == 'node_modules/electron/package.json' for name in contents),
            'ASAR contains an Electron NPM package')
    require(not any(name.startswith('node_modules/@electron/asar/') for name in contents),
            'ASAR contains the build-only packer')
    for provider in runtime_providers:
        package_file = 'node_modules/' + provider['name'] + '/package.json'
        require(package_file in contents,
                f'ASAR is missing common runtime provider {provider["name"]}')
    require(not any(name.startswith('.env') or '/.env' in name for name in contents),
            'ASAR contains a secret or environment file')
    require(asar_path.is_file(), 'upstream ASAR packer produced no app.asar')
    node_sha = digest_file(inventory, node, 'sha256')
    python_sha = digest_file(inventory, Path(native.tool('python')).resolve(strict=True), 'sha256')
    bom = make_projected_sbom(source_manifest, lock, runtime_providers, asar_path,
                               HOST_NODE_VERSION, args.electron_version, args.electron_package_path,
                               args.electron_depends, asar_tool, node_sha,
                               platform.python_version(), python_sha)
    sbom_path.write_bytes(jsonio.json_bytes(bom))
    print(f'Built Ember Browser from Blanc 1.46.0 ({len(contents)} ASAR files) and SBOM.')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except BuildError as exc:
        print(f'build-blanc: {exc}', file=sys.stderr)
        raise SystemExit(1)
