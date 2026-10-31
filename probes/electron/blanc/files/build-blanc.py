#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted package build controller).
"""Build a lockfile-closed Blanc ASAR with the system Electron runtime."""

import argparse
import base64
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
from urllib.parse import urlsplit, quote


MAX_ARCHIVE_BYTES = 512 * 1024 * 1024
MAX_MEMBER_BYTES = 128 * 1024 * 1024
MAX_TOOL_OUTPUT = 8 * 1024 * 1024
NPM_NAME = re.compile(r'^(?:@[a-z0-9._~-]+/)?[a-z0-9._~-]+$')
VERSION = re.compile(r'^[0-9]+\.[0-9]+\.[0-9]+$')
HOST_NODE_VERSION = '26.13.0'
SOURCE_ARCHIVE_SHA256 = 'b241d6b135b0fab5839f5dea6f64fafbdefa4f213b46ffa4a2f78820cb880971'


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


def resolve_package(packages, parent, name):
    require(NPM_NAME.fullmatch(name) is not None, f'invalid NPM dependency name: {name!r}')
    directory = parent
    while True:
        candidate = (directory + '/' if directory else '') + 'node_modules/' + name
        if candidate in packages:
            return candidate
        parent_directory = posixpath.dirname(directory) if directory else '.'
        if parent_directory in ('.', 'node_modules'):
            break
        directory = parent_directory
    root_key = 'node_modules/' + name
    return root_key if root_key in packages else None


def lock_closure(lock):
    require(lock.get('lockfileVersion') == 3, 'Blanc requires package-lock version 3')
    packages = lock.get('packages')
    require(isinstance(packages, dict) and isinstance(packages.get(''), dict),
            'package-lock.json has no root package entry')
    selected = {}
    roles = {}
    edges = {}

    def visit(key, role):
        require(key != 'node_modules/electron',
                'Electron must use the system package, not the Electron NPM package')
        if key in selected:
            roles[key].add(role)
            return
        entry = packages.get(key)
        require(isinstance(entry, dict) and not entry.get('link'),
                f'unsupported lockfile entry: {key}')
        selected[key] = entry
        roles[key] = {role}
        edges[key] = set()
        dependencies = set(entry.get('dependencies', {})) | set(entry.get('optionalDependencies', {}))
        for name in sorted(dependencies):
            child = resolve_package(packages, key, name)
            if child is None and name in entry.get('optionalDependencies', {}):
                continue
            require(child is not None, f'missing locked dependency: {key} -> {name}')
            edges[key].add(child)
            visit(child, role)

    root = packages['']
    for name in sorted(root.get('dependencies', {})):
        key = resolve_package(packages, '', name)
        require(key is not None, f'missing runtime dependency: {name}')
        visit(key, 'runtime')
    require('@electron/asar' in root.get('devDependencies', {}),
            'the locked @electron/asar build tool is required')
    asar = resolve_package(packages, '', '@electron/asar')
    require(asar is not None, 'missing locked @electron/asar package')
    visit(asar, 'build')
    return packages, selected, roles, edges


def digest_file(inventory, path, algorithm):
    return inventory.hash_file(str(path), algorithm)


def archive_members(path):
    try:
        archive = tarfile.open(path, 'r:gz')
    except (OSError, tarfile.TarError) as exc:
        raise BuildError(f'invalid NPM archive {path.name}: {exc}') from exc
    try:
        members = archive.getmembers()
        names = set()
        folded = set()
        total = 0
        for member in members:
            name = member.name
            normalized = name[:-1] if name.endswith('/') else name
            parts = safe_parts(normalized)
            require(parts[0] == 'package', f'archive member is outside package/: {name}')
            require(member.isdir() or member.isreg(), f'link or special archive member: {name}')
            require(normalized not in names, f'duplicate archive member: {name}')
            require(normalized.casefold() not in folded, f'case-colliding archive member: {name}')
            names.add(normalized)
            folded.add(normalized.casefold())
            if member.isreg():
                require(0 <= member.size <= MAX_MEMBER_BYTES, f'oversized NPM archive member: {name}')
                total += member.size
        require(total <= MAX_ARCHIVE_BYTES, f'expanded NPM package is too large: {path.name}')
        require('package/package.json' in names, f'NPM archive has no package/package.json: {path.name}')
        return archive, members
    except BaseException:
        archive.close()
        raise


def extract_verified_package(jsonio, archive_path, destination, expected_name, expected_version):
    require(not destination.exists(), f'refusing existing package directory: {destination}')
    destination.mkdir(parents=True)
    archive, members = archive_members(archive_path)
    try:
        for member in members:
            normalized = member.name[:-1] if member.name.endswith('/') else member.name
            parts = safe_parts(normalized)[1:]
            if not parts:
                continue
            target = destination.joinpath(*parts)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0)
            fd = os.open(target, flags, 0o644)
            source = archive.extractfile(member)
            require(source is not None, f'cannot read NPM archive member: {member.name}')
            remaining = member.size
            try:
                with source, os.fdopen(fd, 'wb') as output:
                    while remaining:
                        chunk = source.read(min(1024 * 1024, remaining))
                        require(bool(chunk), f'truncated NPM archive member: {member.name}')
                        output.write(chunk)
                        remaining -= len(chunk)
            except BaseException:
                try:
                    os.unlink(target)
                except FileNotFoundError:
                    pass
                raise
            lowered = target.name.lower()
            require(not lowered.endswith(('.node', '.so', '.dylib', '.dll')),
                    f'native NPM dependency is not supported: {member.name}')
        package = read_object(jsonio, destination / 'package.json', expected_name)
        require(package.get('name') == expected_name and package.get('version') == expected_version,
                f'NPM metadata does not match the lockfile: {expected_name}@{expected_version}')
        require(not package.get('os') and not package.get('cpu'),
                f'platform-specific package is not supported: {expected_name}')
        scripts = package.get('scripts', {})
        require(not any(name in scripts for name in ('install', 'preinstall', 'postinstall')),
                f'package lifecycle scripts are not run or accepted: {expected_name}')
        return package
    finally:
        archive.close()


def stage_dependencies(jsonio, inventory, source_root, dist_dir, runtime_root, build_root,
                       npm_manifest, expected_manifest_sha256):
    manifest_bytes_sha = digest_file(inventory, npm_manifest, 'sha256')
    require(manifest_bytes_sha == expected_manifest_sha256,
            'NPM mirror manifest does not match its recipe checksum')
    lock_path = source_root / 'package-lock.json'
    lock_bytes_sha = digest_file(inventory, lock_path, 'sha256')
    manifest = read_object(jsonio, npm_manifest, 'NPM mirror manifest')
    require(manifest.get('sourceLockSha256') == lock_bytes_sha,
            'NPM mirror manifest does not match package-lock.json')
    lock = read_object(jsonio, lock_path, 'package-lock.json')
    packages, selected, roles, edges = lock_closure(lock)
    rows = manifest.get('packages')
    require(isinstance(rows, list), 'NPM manifest packages must be a list')
    rows_by_key = {row.get('lockKey'): row for row in rows if isinstance(row, dict)}
    require(len(rows_by_key) == len(rows) == len(selected),
            'NPM mirror manifest package count differs from the lock closure')
    archives = {}
    for key in sorted(selected):
        entry = selected[key]
        row = rows_by_key.get(key)
        require(row is not None, f'missing NPM mirror manifest entry: {key}')
        require(row.get('version') == entry.get('version') and
                row.get('resolved') == entry.get('resolved') and
                row.get('integrity') == entry.get('integrity'),
                f'NPM mirror metadata differs from package-lock.json: {key}')
        role = '+'.join(sorted(roles[key]))
        require(row.get('role') == role, f'NPM package role mismatch: {key}')
        url = urlsplit(entry.get('resolved', ''))
        require(url.scheme == 'https' and url.hostname == 'registry.npmjs.org' and
                not url.username and not url.password and not url.query and not url.fragment,
                f'unapproved NPM dependency source: {entry.get("resolved")}')
        filename = PurePosixPath(url.path).name
        require(row.get('distfile') == filename, f'NPM distfile name mismatch: {key}')
        require(not entry.get('hasInstallScript') and not entry.get('os') and not entry.get('cpu'),
                f'scripted or platform-specific dependency: {key}')
        archive_path = dist_dir / filename
        info = os.lstat(archive_path)
        require(stat.S_ISREG(info.st_mode) and info.st_size == row.get('size'),
                f'NPM archive size mismatch: {key}')
        sha512 = digest_file(inventory, archive_path, 'sha512')
        sha256 = digest_file(inventory, archive_path, 'sha256')
        require(sha512 == row.get('sha512') and sha256 == row.get('sha256'),
                f'NPM archive checksum mismatch: {key}')
        require('sha512-' + base64.b64encode(bytes.fromhex(sha512)).decode('ascii') == entry.get('integrity'),
                f'NPM lock integrity mismatch: {key}')
        archives[key] = (archive_path, row)
    require(not runtime_root.exists() and not build_root.exists(),
            'refusing to reuse a nonempty staged dependency directory')
    runtime_root.mkdir(parents=True)
    build_root.mkdir(parents=True)
    package_metadata = {}
    for key in sorted(selected):
        entry = selected[key]
        name = key.rsplit('node_modules/', 1)[1]
        archive_path, _row = archives[key]
        if 'runtime' in roles[key]:
            package_metadata[key] = extract_verified_package(
                jsonio, archive_path, runtime_root / name, name, entry['version'])
        if 'build' in roles[key]:
            metadata = extract_verified_package(
                jsonio, archive_path, build_root / name, name, entry['version'])
            package_metadata.setdefault(key, metadata)
    require(not (runtime_root / 'electron').exists() and not (build_root / 'electron').exists(),
            'the system Electron runtime must not be copied into Blanc')
    require(not (runtime_root / '@electron' / 'asar').exists(),
            'the build-only ASAR packer must not be copied into Blanc')
    return lock, packages, selected, roles, edges, rows_by_key, package_metadata


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
    expected = f'electron>={version}<{next_patch(version)}:{package_path}'
    require(dependency == expected,
            f'SBOM runtime version and pkgsrc dependency disagree: expected {expected}')
    require(version == '45.2.1', 'Blanc package is qualified only for Electron 45.2.1')
    return expected_path, expected


def make_ref(name, version):
    return f'pkg:npm/{quote(name, safe="/-._~")}@{version}'


def package_license(metadata):
    value = metadata.get('license')
    if value is None:
        return 'NOASSERTION'
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def make_sbom(source_manifest, lock, selected, roles, edges, rows, package_metadata,
              app_asar, node_version, electron_version, electron_pkgpath, electron_dependency,
              asar_name, node_sha256, python_version, python_sha256):
    runtime_path, dependency = validate_runtime_dependency(
        electron_version, electron_pkgpath, electron_dependency)
    lock_sha = source_manifest['packageLockSha256']
    asar_hash = hashlib.sha256(app_asar.read_bytes()).hexdigest()
    root_ref = 'pkg:generic/blanc@1.25.0'
    electron_ref = f'pkgsrc:devel/electron44@{electron_version}'
    components = [{
        'type': 'framework',
        'bom-ref': electron_ref,
        'name': 'Electron',
        'version': electron_version,
        'scope': 'required',
        'properties': [
            {'name': 'emberbsd:external', 'value': 'true'},
            {'name': 'emberbsd:bundled', 'value': 'false'},
            {'name': 'emberbsd:pkgsrcPath', 'value': runtime_path},
            {'name': 'emberbsd:dependency', 'value': dependency},
        ],
    }]
    refs = {}
    for key in sorted(selected):
        entry = selected[key]
        row = rows[key]
        metadata = package_metadata[key]
        name, version = row['name'], entry['version']
        ref = make_ref(name, version)
        refs[key] = ref
        declared_license = package_license(metadata)
        component = {
            'type': 'library',
            'bom-ref': ref,
            'name': name,
            'version': version,
            'scope': 'required' if 'runtime' in roles[key] else 'excluded',
            'hashes': [
                {'alg': 'SHA-512', 'content': row['sha512']},
                {'alg': 'SHA-256', 'content': row['sha256']},
            ],
            'properties': [
                {'name': 'emberbsd:lockKey', 'value': key},
                {'name': 'emberbsd:role', 'value': '+'.join(sorted(roles[key]))},
                {'name': 'emberbsd:npmLicense', 'value': package_license(metadata)},
            ],
        }
        if declared_license != 'NOASSERTION':
            component['licenses'] = [{'license': {'name': declared_license}}]
        components.append(component)
    root_dev = lock.get('packages', {}).get('', {}).get('devDependencies', {})
    locked_dev_packages = lock.get('packages', {})
    upstream_dev_electron = locked_dev_packages.get('node_modules/electron', {})
    root = {
        'type': 'application',
        'bom-ref': root_ref,
        'name': 'Blanc',
        'version': '1.25.0',
        'licenses': [{'license': {'id': 'MIT'}}],
        'hashes': [{'alg': 'SHA-256', 'content': asar_hash}],
        'properties': [
            {'name': 'emberbsd:upstreamCommit', 'value': source_manifest['upstreamCommit']},
            {'name': 'emberbsd:sourceArchiveSha256', 'value': source_manifest['sourceArchiveSha256']},
            {'name': 'emberbsd:packageLockSha256', 'value': lock_sha},
            {'name': 'emberbsd:sourceFileAllowlistSha256', 'value': source_manifest['allowlistSha256']},
            {'name': 'emberbsd:hostNode', 'value': node_version},
            {'name': 'emberbsd:systemElectron', 'value': electron_version},
            {'name': 'emberbsd:systemElectronBundled', 'value': 'false'},
            {'name': 'emberbsd:upstreamDevelopmentElectronVersion',
             'value': upstream_dev_electron.get('version', 'NOASSERTION')},
            {'name': 'emberbsd:upstreamDevelopmentElectronRange',
             'value': root_dev.get('electron', 'NOASSERTION')},
            {'name': 'emberbsd:upstreamDevelopmentElectronBundled', 'value': 'false'},
        ],
    }
    root_package = lock['packages']['']
    root_refs = []
    for name in sorted(root_package.get('dependencies', {})):
        key = resolve_package(lock['packages'], '', name)
        require(key in refs and 'runtime' in roles[key], f'SBOM root dependency is not staged: {name}')
        root_refs.append(refs[key])
    all_refs = [electron_ref] + root_refs
    dependencies = [{'ref': root_ref, 'dependsOn': all_refs}]
    dependencies.append({'ref': electron_ref, 'dependsOn': []})
    for key in sorted(selected):
        if 'runtime' not in roles[key]:
            continue
        child_refs = sorted(refs[child] for child in edges[key] if 'runtime' in roles[child])
        dependencies.append({'ref': refs[key], 'dependsOn': child_refs})
    asar_row = rows['node_modules/@electron/asar']
    build_tools = [
        {'type': 'application', 'name': 'CPython', 'version': python_version,
         'scope': 'excluded', 'hashes': [{'alg': 'SHA-256', 'content': python_sha256}],
         'properties': [{'name': 'emberbsd:role', 'value': 'host-build-only'}]},
        {'type': 'application', 'name': 'Node.js', 'version': node_version,
         'scope': 'excluded', 'hashes': [{'alg': 'SHA-256', 'content': node_sha256}],
         'properties': [{'name': 'emberbsd:role', 'value': 'host-build-only'}]},
        {'type': 'library', 'name': '@electron/asar', 'version': asar_name,
         'scope': 'excluded', 'hashes': [
             {'alg': 'SHA-512', 'content': asar_row['sha512']},
             {'alg': 'SHA-256', 'content': asar_row['sha256']}],
         'properties': [{'name': 'emberbsd:role', 'value': 'host-build-only'}]},
    ]
    return {
        'bomFormat': 'CycloneDX',
        'specVersion': '1.5',
        'version': 1,
        'metadata': {
            'timestamp': source_manifest['upstreamCommitTimestamp'],
            'component': root,
            'tools': {'components': build_tools},
            'properties': [
                {'name': 'emberbsd:sdkApiVersion', 'value': '1'},
                {'name': 'emberbsd:sdkProducerStreamApiVersion', 'value': '1'},
                {'name': 'emberbsd:sdkProducerInspectionApiVersion', 'value': '1'},
            ],
        },
        'components': components,
        'dependencies': dependencies,
    }


def check_source_files(jsonio, inventory, source_root, manifest_path, expected_sha):
    actual_sha = digest_file(inventory, manifest_path, 'sha256')
    require(actual_sha == expected_sha, 'upstream source allowlist does not match the recipe checksum')
    source_manifest = read_object(jsonio, manifest_path, 'upstream source allowlist')
    require(source_manifest.get('schemaVersion') == 2 and
            source_manifest.get('upstreamCommit') == 'ff55d5948f5c71e802ba2ac464659ef96e055ca9' and
            source_manifest.get('packageVersion') == '1.25.0',
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
            'Blanc source distfile checksum differs from the v1.25.0 release archive')
    manifest_sha = digest_file(inventory, manifest_path, 'sha256')
    require(manifest_sha == expected_manifest_sha,
            'upstream source allowlist does not match the recipe checksum')
    manifest = read_object(jsonio, manifest_path, 'upstream source allowlist')
    require(manifest.get('schemaVersion') == 2 and
            manifest.get('upstreamCommit') == 'ff55d5948f5c71e802ba2ac464659ef96e055ca9' and
            manifest.get('packageVersion') == '1.25.0',
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
    archive_prefix = 'blanc-1.25.0/'
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


def run_node_tests(stream, source_root, native, work):
    test_paths = [
        'test/unit/updater-policy.test.js',
        'test/unit/display-capture-netbsd.test.js',
        'test/unit/display-capture-packaged-lock.test.js',
        'test/unit/display-capture-platform-lock.test.js',
    ]
    output = run_host_tool(stream, [native.tool('node'), '--test', *(str(source_root / p) for p in test_paths)], cwd=source_root,
                           env=child_environment(native, work), timeout=300)
    sys.stdout.buffer.write(output)


def run_python_tests(stream, source_root, dist_dir, native, work, sdk_root):
    test_path = Path(__file__).parent / 'test_blanc_package.py'
    output = run_host_tool(stream, [native.tool('python'), '-B', '-I', '-S', str(test_path),
                                    '--sdk-source', str(sdk_root), '--source', str(source_root),
                                    '--distdir', str(dist_dir)],
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
    parser.add_argument('--source-archive-sha256')
    parser.add_argument('--source-files-sha256')
    parser.add_argument('--electron-version')
    parser.add_argument('--electron-package-path')
    parser.add_argument('--electron-depends')
    return parser.parse_args()


def main():
    args = parse_args()
    sdk_root, jsonio, inventory, stream, native_api = load_sdk(args.sdk_source)
    require(sys.version_info >= (3, 15), 'Blanc package tools require host Python 3.15 or newer')
    require(args.source_archive_sha256 == SOURCE_ARCHIVE_SHA256,
            'Blanc source distfile checksum differs from the v1.25.0 release archive')
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
    require(args.distdir and args.work and args.node and args.host_prefix and args.source_archive_sha256 and
            args.source_files_sha256 and args.electron_version and args.electron_package_path and
            args.electron_depends, 'build and test require all pinned host, source, and runtime arguments')
    native = select_host_tools(native_api, args.host_prefix, args.node)
    source_root = Path(args.source).resolve(strict=True)
    dist_dir = Path(args.distdir).resolve(strict=True)
    work = Path(args.work).resolve(strict=True)
    (work / 'tmp').mkdir(exist_ok=True)
    (work / 'home').mkdir(exist_ok=True)
    node = Path(native.tool('node'))
    env = child_environment(native, work)
    node_version = run_host_tool(stream, [str(node), '--version'], cwd=work, env=env, timeout=30)
    validate_host_node_version(node_version)
    manifest_path = Path(__file__).parent / 'npm-mirror-manifest.json'
    source_manifest = check_source_files(
        jsonio, inventory, source_root, source_list_path,
        args.source_files_sha256)
    source_manifest['sourceArchiveSha256'] = args.source_archive_sha256
    validate_runtime_dependency(args.electron_version, args.electron_package_path, args.electron_depends)
    run_node_tests(stream, source_root, native, work)
    if args.action == 'test':
        run_python_tests(stream, source_root, dist_dir, native, work, sdk_root)
        return 0

    runtime_root = work / 'runtime-node-modules'
    build_root = work / 'asar-tools' / 'node_modules'
    app_root = work / 'app-stage'
    seed_root = work / 'seed-inputs'
    asar_path = work / 'app.asar'
    sbom_path = work / 'SBOM.json'
    npm_manifest_sha = '6f5e82b752db384b728e1d6caf357eb86d0652f0441b527d559de2f6ad396209'
    lock, packages, selected, roles, edges, rows, package_metadata = stage_dependencies(
        jsonio, inventory, source_root, dist_dir, runtime_root, build_root,
        manifest_path, npm_manifest_sha)
    require(not app_root.exists() and not seed_root.exists() and not asar_path.exists() and not sbom_path.exists(),
            'refusing to overwrite existing Blanc build output')
    copy_allowlist(source_root, source_manifest['applicationFiles'], app_root)
    copy_module_tree(runtime_root, app_root / 'node_modules')
    copy_allowlist(source_root, source_manifest['buildInputs'] + source_manifest['generatedFiles'], seed_root)
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
    asar_api = build_root / '@electron/asar/lib/asar.js'
    asar_wrapper = Path(__file__).parent / 'asar-pack.mjs'
    asar_output = run_host_tool(stream, [str(node), str(asar_wrapper), str(asar_api), str(app_root), str(asar_path)],
                                cwd=work, env=env, timeout=900)
    packed = jsonio.loads_json(asar_output)
    require(isinstance(packed, dict), 'ASAR packer result must be a JSON object')
    contents = packed.get('files')
    require(isinstance(contents, list), 'ASAR packer returned no file list')
    for relative in (
        'package.json', 'src/main/main.js', 'src/main/assets/adblock-engine-seed.bin',
        'node_modules/@ghostery/adblocker-electron/package.json',
    ):
        require(relative in contents, f'ASAR is missing required application input: {relative}')
    require(not any(name == 'node_modules/electron/package.json' for name in contents),
            'ASAR contains an Electron NPM package')
    require(not any(name.startswith('node_modules/@electron/asar/') for name in contents),
            'ASAR contains the build-only packer')
    require(not any(name.startswith('.env') or '/.env' in name for name in contents),
            'ASAR contains a secret or environment file')
    require(asar_path.is_file(), 'upstream ASAR packer produced no app.asar')
    node_sha = digest_file(inventory, node, 'sha256')
    python_sha = digest_file(inventory, Path(native.tool('python')).resolve(strict=True), 'sha256')
    bom = make_sbom(source_manifest, lock, selected, roles, edges, rows, package_metadata,
                    asar_path, HOST_NODE_VERSION, args.electron_version, args.electron_package_path,
                    args.electron_depends, packages['node_modules/@electron/asar']['version'], node_sha,
                    platform.python_version(), python_sha)
    sbom_path.write_bytes(jsonio.json_bytes(bom))
    print(f'Built Blanc 1.25.0 app.asar ({len(contents)} files) and external-runtime SBOM.')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except BuildError as exc:
        print(f'build-blanc: {exc}', file=sys.stderr)
        raise SystemExit(1)
