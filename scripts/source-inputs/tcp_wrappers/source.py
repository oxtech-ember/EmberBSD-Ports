#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Prepare and verify the pinned common pkgsrc tcp_wrappers source."""
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
PACKAGE = 'security/tcp_wrappers'
sys.path.insert(0, str(PORTS / 'pkgsrc/lang/llvm/files'))
import sdk_source


def load_sdk(argv):
    sdk, argv = sdk_source.load_sdk(argv)
    globals()['SDK_SOURCE'] = sdk
    from emberbsd_sdk import jsonio, paths, process, sourceprep
    from emberbsd_sdk.errors import SDKError
    from emberbsd_sdk.publication import publish_directory_noreplace
    if getattr(sourceprep, 'PREPARED_TREE_API', None) != 1:
        raise SDKError('selected SDK lacks the prepared source tree API')
    globals().update(jsonio=jsonio, paths=paths, process=process, sourceprep=sourceprep,
                     SDKError=SDKError, publish_directory_noreplace=publish_directory_noreplace)
    return argv


def require(condition, message):
    if not condition:
        raise SDKError(message)


def read(path):
    handle, before = paths.open_regular(path)
    with handle:
        data = handle.read()
    paths.verify_stable(path, before)
    return data


def digest(data):
    return hashlib.sha256(data).hexdigest()


def identity_module():
    module_path = PORTS / 'scripts/pkgsrc-source-identity.py'
    spec = importlib.util.spec_from_file_location('pkgsrc_source_identity', module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source_identity(git):
    module = identity_module()
    return {'export': module.identity(PORTS, PACKAGE, git, SDK_SOURCE),
            'owner_sha256': digest(read(Path(__file__).resolve()))}


def recipe(exported):
    recipe_root = Path(exported) / PACKAGE
    common = read(recipe_root / 'Makefile')
    matches = re.findall(rb'^DISTNAME=\s*(tcp_wrappers_[0-9]+(?:\.[0-9]+)+-ipv6\.[0-9]+)$', common, re.M)
    require(len(matches) == 1, 'ambiguous tcp_wrappers release')
    distname = matches[0].decode('ascii')
    archive = distname + '.tar.gz'
    info = read(recipe_root / 'distinfo').decode('utf-8')
    hashes = {}
    for label, key in (('SHA512', 'sha512'), ('BLAKE2s', 'blake2s'), ('Size', 'size')):
        values = re.findall(r'^' + label + r' \(' + re.escape(archive) + r'\) = (\S+)(?: bytes)?$', info, re.M)
        require(len(values) == 1, 'ambiguous tcp_wrappers archive ' + label)
        hashes[key] = int(values[0]) if key == 'size' else values[0]
    declared = re.findall(r'^SHA1 \((patch-[^)]+)\) = ([0-9a-f]{40})$', info, re.M)
    patches = sorted((recipe_root / 'patches').glob('patch-*'))
    require([p.name for p in patches] == sorted(name for name, _ in declared),
            'tcp_wrappers patch inventory differs from distinfo')
    for name, expected in declared:
        data = read(recipe_root / 'patches' / name)
        filtered = b''.join(line for line in data.splitlines(keepends=True) if b'$NetBSD' not in line)
        require(hashlib.sha1(filtered).hexdigest() == expected, 'tcp_wrappers patch checksum differs: ' + name)
    inputs = [recipe_root / 'Makefile', recipe_root / 'distinfo', *patches]
    identity = dict(distname=distname, archive=archive, **hashes,
                    recipe={str(path.relative_to(recipe_root)): digest(read(path)) for path in inputs})
    return identity, patches


def verify(source, git, archive=None, patch=None):
    identity = source_identity(git)
    record = jsonio.read_json(str(Path(source) / sourceprep.PREPARED_TREE_RECEIPT))
    old = record.get('identity') if isinstance(record, dict) else None
    record = sourceprep.validate_prepared_tree(source, package=PACKAGE, identity=old)
    if old == identity:
        return record
    if isinstance(old, dict) and set(old) == {'effective', 'owner_sha256'}:
        require(isinstance(old['owner_sha256'], str) and re.fullmatch('[0-9a-f]{64}', old['owner_sha256']),
                'invalid scoped tcp_wrappers owner identity')
        require(patch and os.path.isabs(patch), 'effective tcp_wrappers verification requires an explicit patch')
        with tempfile.TemporaryDirectory(prefix='.tcp_wrappers-verify-') as tmp:
            exported = Path(tmp) / 'pkgsrc'
            process.capture([sys.executable, '-B', str(PORTS / 'scripts/prepare-pkgsrc.py'),
                             str(exported), '--git', git, '--patch', patch],
                            env=process.sanitized_environment())
            selector = identity_module()
            current = selector.effective_package_identity(exported, PACKAGE, identity['export']['upstream'])
            require(identity == source_identity(git), 'pkgsrc export inputs changed during verification')
            require(selector.equivalent_effective_package(old['effective'], old['effective']) and
                    old['effective']['package'] == PACKAGE,
                    'invalid scoped tcp_wrappers package identity')
            if (not selector.equivalent_effective_package(old['effective'], current) or
                    old['owner_sha256'] != identity['owner_sha256']):
                require(archive and os.path.isabs(archive),
                        'changed tcp_wrappers inputs require an explicit archive for payload comparison')
                prepared = prepare(archive, Path(tmp) / 'expected', patch, git)
                require(identity == source_identity(git), 'pkgsrc export inputs changed during verification')
                require(prepared['tree_sha256'] == record['tree_sha256'],
                        'prepared tcp_wrappers differs from current effective source')
        return record
    export = old.get('export') if isinstance(old, dict) else None
    require(isinstance(export, dict) and set(old) == {'export', 'owner_sha256'} and
            set(export) == {'api', 'package', 'export_inputs_sha256', 'upstream'} and
            type(export['api']) is int and export['api'] == 1 and export['package'] == PACKAGE and
            isinstance(export['export_inputs_sha256'], str) and re.fullmatch('[0-9a-f]{64}', export['export_inputs_sha256']) and
            isinstance(export['upstream'], str) and re.fullmatch('[0-9a-f]{40}', export['upstream']) and
            isinstance(old['owner_sha256'], str) and re.fullmatch('[0-9a-f]{64}', old['owner_sha256']),
            'unrecognized legacy tcp_wrappers identity')
    require(archive and patch and os.path.isabs(archive) and os.path.isabs(patch),
            'changed export requires an explicit archive and patch to compare tcp_wrappers')
    with tempfile.TemporaryDirectory(prefix='.tcp_wrappers-verify-') as tmp:
        expected = Path(tmp) / 'expected'
        prepared = prepare(archive, expected, patch, git)
        require(identity == source_identity(git), 'pkgsrc export inputs changed during verification')
        require(prepared['tree_sha256'] == record['tree_sha256'],
                'prepared tcp_wrappers differs from current effective source')
    return record


def prepare(archive, output, patch, git, scoped_identity=False):
    require(os.path.isabs(git) and os.path.isabs(patch), 'select absolute Git and patch executables')
    output = Path(output)
    require(output.is_absolute(), 'prepared source output must be absolute')
    output = Path(paths.canonical_existing(output.parent), output.name)
    require(not os.path.lexists(output), 'prepared source output already exists')
    paths.reject_overlap(str(output), str(PORTS))
    identity = source_identity(git)
    with tempfile.TemporaryDirectory(prefix='.tcp_wrappers-source-', dir=output.parent) as tmp:
        tmp = Path(tmp)
        exported = tmp / 'pkgsrc'
        process.capture([sys.executable, '-B', str(PORTS / 'scripts/prepare-pkgsrc.py'),
                         str(exported), '--git', git, '--patch', patch],
                        env=process.sanitized_environment())
        metadata, patches = recipe(exported)
        archive = Path(paths.canonical_existing(archive))
        require(archive.name == metadata['archive'], 'tcp_wrappers archive filename differs from recipe')
        data = read(archive)
        hashes = sourceprep.archive_hashes(data)
        require(all(hashes[key] == metadata[key] for key in ('sha512', 'blake2s', 'size')),
                'tcp_wrappers archive checksum differs from recipe')
        packed = tmp / archive.name
        packed.write_bytes(data)
        sourceprep.extract_archive(packed, tmp, metadata['distname'], 'tcp_wrappers')
        root = tmp / metadata['distname']
        for index, path in enumerate(patches):
            delta = read(path)
            require(digest(delta) == metadata['recipe']['patches/' + path.name], 'tcp_wrappers patch changed')
            sourceprep.apply_patch(patch, path, delta, root, 'tcp_wrappers',
                patch_args=('-p0', '-f', '-N', '-F0', '-V', 'none'),
                allow_dev_null=True,
                backup_directory=tmp / ('patch-backups-' + str(index)))
        require(not any(p.name.endswith(('.orig', '.rej')) for p in root.rglob('*')),
                'tcp_wrappers patch left a backup or reject')
        require(identity == source_identity(git), 'pkgsrc export inputs changed during preparation')
        if scoped_identity:
            selector = identity_module()
            identity = {'effective': selector.effective_package_identity(exported, PACKAGE, identity['export']['upstream']),
                        'owner_sha256': identity['owner_sha256']}
        record = sourceprep.write_prepared_tree_receipt(root, package=PACKAGE, identity=identity)
        sourceprep.validate_prepared_tree(root, package=PACKAGE, identity=identity)
        require(sourceprep.archive_hashes(read(archive)) == hashes, 'tcp_wrappers archive changed during preparation')
        publish_directory_noreplace(root, output)
    return record


def main():
    sdk_source.install_signal_handlers()
    args = load_sdk(sys.argv[1:])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--git', required=True, help='absolute Git inspector')
    sub = parser.add_subparsers(dest='action', required=True)
    produce = sub.add_parser('prepare')
    produce.add_argument('--archive', required=True)
    produce.add_argument('--output', required=True)
    produce.add_argument('--patch', required=True)
    produce.add_argument('--scoped-identity', action='store_true')
    check = sub.add_parser('verify-source')
    check.add_argument('--source', required=True)
    check.add_argument('--archive')
    check.add_argument('--patch')
    selected = parser.parse_args(args)
    try:
        if selected.action == 'prepare':
            record = prepare(selected.archive, selected.output, selected.patch, selected.git, selected.scoped_identity)
        else:
            record = verify(selected.source, selected.git, selected.archive, selected.patch)
        sys.stdout.buffer.write(jsonio.json_bytes(record))
    except (SDKError, OSError, ValueError) as exc:
        sdk_source.exit_error(exc, 'tcp_wrappers source: ')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        sdk_source.exit_error(error, 'tcp_wrappers source: ')
