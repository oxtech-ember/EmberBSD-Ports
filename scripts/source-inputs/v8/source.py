#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Prepare and verify the common V8 source from the effective Ports recipe."""
import argparse
import hashlib
import importlib.util
import os
from pathlib import Path
import re
import sys
import tempfile

sys.dont_write_bytecode = True
PORTS = Path(__file__).resolve().parents[3]
PACKAGE = 'lang/v8'
sys.path.insert(0, str(PORTS / 'pkgsrc/lang/llvm/files'))
import sdk_source
sys.path.append(str(PORTS / 'scripts'))
import prepared_receipt


def read(path):
    handle, before = paths.open_regular(path)
    with handle:
        data = handle.read()
    paths.verify_stable(path, before)
    return data


def digest(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise SDKError(message)


def selector():
    spec = importlib.util.spec_from_file_location('pkgsrc_source_identity', PORTS / 'scripts/pkgsrc-source-identity.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def identity(git):
    return {'export': selector().identity(PORTS, PACKAGE, git, sdk),
            'owner_sha256': digest(read(Path(__file__).resolve()))}


def recipe(exported):
    root = Path(exported) / PACKAGE
    make = read(root / 'Makefile')
    revision = re.findall(rb'^V8_REVISION=\s*([0-9a-f]{40})$', make, re.M)
    version = re.findall(rb'^V8_VERSION=\s*([0-9]+(?:\.[0-9]+){3})$', make, re.M)
    require(len(revision) == len(version) == 1, 'ambiguous V8 revision or version')
    rev, ver = revision[0].decode(), version[0].decode()
    archive = f'v8-{ver}-{rev}.tar.gz'
    info = read(root / 'distinfo').decode('utf-8')
    values = {}
    for label, key in (('BLAKE2s', 'blake2s'), ('SHA512', 'sha512'), ('Size', 'size')):
        matches = re.findall(r'^' + label + r' \(' + re.escape(archive) + r'\) = (\S+)(?: bytes)?$', info, re.M)
        require(len(matches) == 1, 'ambiguous V8 archive ' + label)
        values[key] = int(matches[0]) if key == 'size' else matches[0]
    declared = re.findall(r'^SHA1 \((patch-[^)]+)\) = ([0-9a-f]{40})$', info, re.M)
    patches = sorted((root / 'patches').glob('patch-*'))
    require([p.name for p in patches] == sorted(name for name, _ in declared), 'V8 patch inventory differs from distinfo')
    for name, expected in declared:
        data = read(root / 'patches' / name)
        filtered = b''.join(line for line in data.splitlines(keepends=True) if b'$NetBSD' not in line)
        require(hashlib.sha1(filtered).hexdigest() == expected, 'V8 patch checksum differs: ' + name)
    return {'revision': rev, 'version': ver, 'archive': archive, **values,
            'patches': {p.name: digest(read(p)) for p in patches}}, patches


def prepare(archive, output, patch, git):
    require(git and patch and os.path.isabs(git) and os.path.isabs(patch), 'select absolute Git and patch tools')
    output = Path(output)
    require(output.is_absolute(), 'output must be absolute')
    output = Path(paths.canonical_existing(output.parent), output.name)
    require(not os.path.lexists(output), 'output already exists')
    paths.reject_overlap(str(output), str(PORTS))
    before = identity(git)
    with tempfile.TemporaryDirectory(prefix='.v8-source-', dir=output.parent) as directory:
        tmp = Path(directory)
        exported = tmp / 'pkgsrc'
        process.capture([sys.executable, '-B', str(PORTS / 'scripts/prepare-pkgsrc.py'), str(exported),
                         '--git', git, '--patch', patch], env=process.sanitized_environment())
        metadata, patches = recipe(exported)
        archive = Path(paths.canonical_existing(archive))
        require(archive.name == metadata['archive'], 'archive filename differs from recipe')
        data = read(archive)
        hashes = sourceprep.archive_hashes(data)
        require(all(hashes[key] == metadata[key] for key in ('blake2s', 'sha512', 'size')),
                'archive checksum differs from recipe')
        packed = tmp / archive.name
        packed.write_bytes(data)
        name = 'v8-' + metadata['revision']
        sourceprep.extract_archive(packed, tmp, name, 'V8', max_bytes=512 * 1024 * 1024)
        root = tmp / name
        header = read(root / 'include/v8-version.h')
        components = []
        for macro in ('V8_MAJOR_VERSION', 'V8_MINOR_VERSION', 'V8_BUILD_NUMBER', 'V8_PATCH_LEVEL'):
            found = re.findall(rb'^#define ' + macro.encode() + rb' ([0-9]+)$', header, re.M)
            require(len(found) == 1, 'ambiguous V8 header version')
            components.append(found[0].decode())
        require('.'.join(components) == metadata['version'], 'V8 header version differs from recipe')
        original_backups = {p.relative_to(root) for p in root.rglob('*') if p.name.endswith(('.orig', '.rej'))}
        for index, patch_path in enumerate(patches):
            delta = read(patch_path)
            require(digest(delta) == metadata['patches'][patch_path.name], 'V8 patch changed during preparation')
            sourceprep.apply_patch(patch, patch_path, delta, root, 'V8',
                patch_args=('-p0', '-f', '-N', '-F0', '-V', 'none'),
                backup_directory=tmp / ('patch-backups-' + str(index)), allow_dev_null=True)
        require({p.relative_to(root) for p in root.rglob('*') if p.name.endswith(('.orig', '.rej'))} == original_backups,
                'patch left a backup or reject')
        require(before == identity(git), 'source inputs changed during preparation')
        scoped = {'effective': selector().effective_package_identity(exported, PACKAGE, before['export']['upstream']),
                  'owner_sha256': before['owner_sha256']}
        record = prepared_receipt.write(root, package=PACKAGE, identity=scoped)
        require(sourceprep.archive_hashes(read(archive)) == hashes, 'archive changed during preparation')
        publish_directory_noreplace(root, output)
    return record


def verify_payload(source):
    record = jsonio.read_json(str(Path(source) / sourceprep.PREPARED_TREE_RECEIPT))
    old = record.get('identity') if isinstance(record, dict) else None
    sourceprep.validate_prepared_tree(source, package=PACKAGE, identity=old)
    return record


def verify_source(source, pkgsrc_root):
    require(os.path.isabs(pkgsrc_root), 'select an absolute prepared pkgsrc export')
    record = verify_payload(source)
    old = record['identity']
    require(isinstance(old, dict) and set(old) in ({'effective'}, {'effective', 'owner_sha256'}),
            'source receipt lacks an effective V8 recipe')
    if 'owner_sha256' in old:
        require(old['owner_sha256'] == digest(read(Path(__file__).resolve())), 'V8 source producer changed')
    module = selector()
    require(module.equivalent_effective_package(old['effective'], old['effective']) and
            old['effective']['package'] == PACKAGE, 'invalid V8 effective package identity')
    current = module.effective_package_identity(pkgsrc_root, PACKAGE, old['effective']['upstream'])
    require(module.equivalent_effective_package(old['effective'], current), 'V8 effective recipe changed')
    return record


def main():
    global sdk, paths, sourceprep, process, jsonio, SDKError, publish_directory_noreplace
    sdk_source.install_signal_handlers()
    sdk, args = sdk_source.load_sdk(sys.argv[1:])
    from emberbsd_sdk import jsonio, paths, process, sourceprep
    from emberbsd_sdk.errors import SDKError
    from emberbsd_sdk.publication import publish_directory_noreplace
    require(getattr(sourceprep, 'PREPARED_TREE_API', None) == 1, 'selected SDK lacks prepared tree API')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--git', help='absolute Git inspector for preparation')
    commands = parser.add_subparsers(dest='action', required=True)
    build = commands.add_parser('prepare')
    for name in ('archive', 'output', 'patch'):
        build.add_argument('--' + name, required=True)
    payload = commands.add_parser('verify-payload')
    payload.add_argument('--source', required=True)
    check = commands.add_parser('verify-source')
    check.add_argument('--source', required=True)
    check.add_argument('--pkgsrc-root', required=True)
    args = parser.parse_args(args)
    try:
        if args.action == 'prepare':
            result = prepare(args.archive, args.output, args.patch, args.git)
        elif args.action == 'verify-payload':
            result = verify_payload(args.source)
        else:
            result = verify_source(args.source, args.pkgsrc_root)
        sys.stdout.buffer.write(jsonio.json_bytes(result))
    except (SDKError, OSError, ValueError) as exc:
        sdk_source.exit_error(exc, 'V8 source: ')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        sdk_source.exit_error(exc, 'V8 source: ')
