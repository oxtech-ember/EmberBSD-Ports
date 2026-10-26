#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Prepare the common LLVM runtime source for Ports and native OS consumers."""
import hashlib
import os
from pathlib import Path
import re
import sys
import tempfile

sys.dont_write_bytecode = True
OWNER = Path(__file__).resolve().parents[1]
PORTS = OWNER.parents[2]
SOURCE_MANIFEST = 'llvm-source.json'
RECIPE = 'pkgsrc/lang/compiler-rt'


def load_sdk(arguments):
    # This is the common Ports loader, shared with the LLVM compiler recipe.
    sys.path.insert(0, str(OWNER.parent / 'llvm/files'))
    import sdk_source
    sdk_source.install_signal_handlers()
    _, arguments = sdk_source.load_sdk(arguments)
    from emberbsd_sdk import inventory, jsonio, paths, process, sourceprep
    from emberbsd_sdk.errors import SDKError
    from emberbsd_sdk.publication import publish_directory_noreplace
    if sourceprep.SOURCE_PREPARATION_API != 2:
        raise SDKError('LLVM runtime preparation requires SDK source preparation API 2')
    globals().update(inventory=inventory, jsonio=jsonio, paths=paths,
                     process=process, sourceprep=sourceprep, SDKError=SDKError,
                     publish_directory_noreplace=publish_directory_noreplace)
    return arguments


def require(condition, message):
    if not condition:
        raise SDKError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    handle, before = paths.open_regular(path)
    with handle:
        data = handle.read()
    paths.verify_stable(path, before)
    return data


def git_revision(git, root):
    require(os.path.isabs(git), 'select an absolute Git executable')
    revision = process.capture([git, '-C', str(root), 'rev-parse', 'HEAD'],
                               env=process.sanitized_environment()).stdout.decode().strip()
    require(re.fullmatch('[0-9a-f]{40}', revision), 'invalid source revision')
    return revision


def patch_inventory(directory, info, label):
    declared = re.findall(r'^SHA1 \((patch-[^)]+)\) = ([0-9a-f]{40})$', info, re.M)
    patches = sorted(directory.glob('patch-*'))
    require([p.name for p in patches] == sorted(name for name, _ in declared),
            'undeclared or duplicate ' + label + ' patch')
    for name, expected in declared:
        data = read(directory / name)
        filtered = b''.join(line for line in data.splitlines(True) if b'$NetBSD' not in line)
        require(hashlib.sha1(filtered).hexdigest() == expected, label + ' patch checksum differs: ' + name)
    return patches


def recipe(git):
    """Read one current version/archive owner and the complete runtime patch set."""
    version_file = PORTS / 'pkgsrc/lang/llvm/version.mk'
    match = re.search(rb'^LLVM_VERSION=\s*([0-9]+\.[0-9]+\.[0-9]+)$', read(version_file), re.M)
    require(match is not None, 'missing common LLVM version')
    version = match[1].decode()
    archive_name = 'llvm-project-' + version + '.src.tar.xz'
    distinfo = PORTS / 'pkgsrc/lang/llvm/distinfo'
    info = read(distinfo).decode()
    patchinfo = OWNER / 'distinfo'
    package_info = read(patchinfo).decode()
    hashes = {}
    for algorithm, key in (('SHA512', 'sha512'), ('BLAKE2s', 'blake2s'), ('Size', 'size')):
        values = re.findall(r'^' + algorithm + r' \(' + re.escape(archive_name) + r'\) = (\S+)(?: bytes)?$', info, re.M)
        require(len(values) == 1, 'ambiguous common LLVM archive ' + algorithm)
        package_values = re.findall(r'^' + algorithm + r' \(' + re.escape(archive_name) + r'\) = (\S+)(?: bytes)?$', package_info, re.M)
        require(package_values == values, 'compiler-rt archive selection differs from LLVM: ' + algorithm)
        hashes[key] = int(values[0]) if key == 'size' else values[0]
    component_file = OWNER / 'files/source-components.json'
    components = jsonio.read_json(component_file)
    require(isinstance(components, list) and components and
            len(set(components)) == len(components) and
            all(isinstance(name, str) and re.fullmatch('[a-z-]+(?:/[a-z-]+)*', name)
                for name in components), 'invalid common runtime components')
    patches = [(path, '.', 1) for path in
               patch_inventory(OWNER / 'patches', package_info, 'common runtime')]
    # The runtime source also consumes LLVM CMake modules. Reuse their common
    # patches in place; compiler-rt must not maintain another copy of them.
    for path in patch_inventory(PORTS / 'pkgsrc/lang/llvm/patches', info, 'common LLVM'):
        names = re.findall(rb'^\+\+\+ ([^\t\n ]+)', read(path), re.M)
        require(bool(names), 'LLVM patch has no source paths: ' + path.name)
        applies = [name.startswith(b'cmake/') for name in names]
        require(all(applies) or not any(applies), 'LLVM patch mixes runtime CMake and other sources: ' + path.name)
        if all(applies):
            patches.append((path, 'llvm', 0))
    inputs = [version_file, distinfo, component_file, patchinfo, Path(__file__).resolve(),
              *(path for path, _, _ in patches)]
    return dict(llvm_version=version, components=components,
                source=dict(archive=archive_name, **hashes),
                recipe=dict(ports_revision=git_revision(git, PORTS),
                            files={str(p.relative_to(PORTS)): digest(read(p)) for p in inputs})), patches


def tree_hash(source):
    return digest(jsonio.json_bytes(inventory.snapshot_tree(str(source), exclude=(SOURCE_MANIFEST,))))


def verify_source(source, git):
    source = Path(paths.canonical_existing(source))
    record = jsonio.read_json(source / SOURCE_MANIFEST)
    require(isinstance(record, dict) and set(record) == {
        'format', 'version', 'llvm_version', 'components', 'source', 'recipe', 'tree_sha256'},
        'invalid LLVM source manifest')
    require(record['format'] == 'emberbsd-llvm-source' and type(record['version']) is int and
            record['version'] == 1, 'unsupported LLVM source manifest')
    current, _ = recipe(git)
    for key in ('llvm_version', 'components', 'source'):
        require(record[key] == current[key], 'LLVM prepared source selection changed: ' + key)
    require(isinstance(record['recipe'], dict) and set(record['recipe']) == {'ports_revision', 'files'} and
            re.fullmatch('[0-9a-f]{40}', record['recipe'].get('ports_revision', '')) and
            record['recipe']['files'] == current['recipe']['files'], 'LLVM prepared recipe inputs changed')
    # Unrelated Ports commits do not require preparing the same source again.
    require(record['tree_sha256'] == tree_hash(source), 'LLVM prepared source tree changed')
    return record


def prepare_source(archive, source, patch, git):
    metadata, patches = recipe(git)
    archive = Path(paths.canonical_existing(archive))
    require(archive.name == metadata['source']['archive'], 'LLVM archive basename differs from the common recipe')
    data = read(archive)
    hashes = sourceprep.archive_hashes(data)
    require(all(hashes[key] == metadata['source'][key] for key in ('sha512', 'blake2s', 'size')),
            'LLVM archive bytes differ from the common recipe')
    require(os.path.isabs(patch), 'select an absolute patch executable')
    source = Path(source)
    require(source.is_absolute(), 'select an absolute new source root')
    source = Path(paths.canonical_existing(source.parent), source.name)
    require(not os.path.lexists(source), 'LLVM source output already exists')
    paths.reject_overlap(str(source), str(PORTS))
    with tempfile.TemporaryDirectory(prefix='.llvm-runtime-', dir=source.parent) as temp:
        temp = Path(temp)
        packed = temp / archive.name
        packed.write_bytes(data)
        root_name = archive.name.removesuffix('.tar.xz')
        sourceprep.extract_archive(packed, temp, root_name, 'LLVM runtimes',
                                   components=metadata['components'], max_members=500000,
                                   max_bytes=4 * 1024**3)
        root = temp / root_name
        for path, subdirectory, strip in patches:
            delta = read(path)
            require(digest(delta) == metadata['recipe']['files'][str(path.relative_to(PORTS))],
                    'LLVM runtime patch changed before application')
            staged = temp / path.name
            staged.write_bytes(delta)
            sourceprep.apply_patch(patch, staged, delta, root / subdirectory, 'LLVM runtimes',
                                   patch_args=('-p' + str(strip), '-f', '-N', '-F0', '-V', 'none'), allow_dev_null=True)
        require(not any(p.name.endswith(('.orig', '.rej')) for p in root.rglob('*')),
                'LLVM patch left backup or reject files')
        record = dict(format='emberbsd-llvm-source', version=1, **metadata,
                      tree_sha256=tree_hash(root))
        jsonio.write_json(root / SOURCE_MANIFEST, record)
        verify_source(root, git)
        require(inventory.sha256_file(archive) == hashes['sha256'], 'LLVM archive changed during preparation')
        publish_directory_noreplace(root, source)
    return record
