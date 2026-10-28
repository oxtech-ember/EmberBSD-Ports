#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Prepare and verify the pinned common pkgsrc Node.js source."""
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
PACKAGE = 'lang/nodejs'
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


def source_identity(git):
    module_path = PORTS / 'scripts/pkgsrc-source-identity.py'
    spec = importlib.util.spec_from_file_location('pkgsrc_source_identity', module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return {'export': module.identity(PORTS, PACKAGE, git, SDK_SOURCE),
            'owner_sha256': digest(read(Path(__file__).resolve()))}


def recipe(exported):
    recipe_root = Path(exported) / PACKAGE
    common = read(recipe_root / 'Makefile')
    matches = re.findall(rb'^DISTNAME=\s*(node-v[0-9]+\.[0-9]+\.[0-9]+)$', common, re.M)
    require(len(matches) == 1, 'ambiguous Node.js release')
    distname = matches[0].decode('ascii')
    suffix = re.findall(rb'^EXTRACT_SUFX=\s*(\.tar\.[a-z0-9]+)$', common, re.M)
    require(len(suffix) == 1, 'ambiguous Node.js archive suffix')
    archive = distname + suffix[0].decode('ascii')
    info = read(recipe_root / 'distinfo').decode('utf-8')
    hashes = {}
    for label, key in (('SHA512', 'sha512'), ('BLAKE2s', 'blake2s'), ('Size', 'size')):
        values = re.findall(r'^' + label + r' \(' + re.escape(archive) + r'\) = (\S+)(?: bytes)?$', info, re.M)
        require(len(values) == 1, 'ambiguous Node.js archive ' + label)
        hashes[key] = int(values[0]) if key == 'size' else values[0]
    declared = re.findall(r'^SHA1 \((patch-[^)]+)\) = ([0-9a-f]{40})$', info, re.M)
    patches = sorted((recipe_root / 'patches').glob('patch-*'))
    require([p.name for p in patches] == sorted(name for name, _ in declared),
            'Node.js patch inventory differs from distinfo')
    for name, expected in declared:
        data = read(recipe_root / 'patches' / name)
        filtered = b''.join(line for line in data.splitlines(keepends=True) if b'$NetBSD' not in line)
        require(hashlib.sha1(filtered).hexdigest() == expected, 'Node.js patch checksum differs: ' + name)
    inputs = [recipe_root / 'Makefile', recipe_root / 'distinfo', *patches]
    identity = dict(distname=distname, archive=archive, **hashes,
                    recipe={str(path.relative_to(recipe_root)): digest(read(path)) for path in inputs})
    return identity, patches


def identity_module():
    module_path = PORTS / 'scripts/pkgsrc-source-identity.py'
    spec = importlib.util.spec_from_file_location('pkgsrc_source_identity', module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_payload(source):
    record = jsonio.read_json(Path(source) / sourceprep.PREPARED_TREE_RECEIPT)
    require(isinstance(record, dict) and isinstance(record.get('identity'), dict),
            'invalid Node.js prepared source receipt')
    return sourceprep.validate_prepared_tree(source, package=PACKAGE, identity=record['identity'])


def verify_source(source, pkgsrc_root):
    record = verify_payload(source)
    identity = record['identity']
    require(set(identity) == {'effective', 'owner_sha256'} and
            identity['owner_sha256'] == digest(read(Path(__file__).resolve())),
            'Node.js source owner changed or receipt requires re-preparation')
    selector = identity_module()
    old = identity['effective']
    require(selector.equivalent_effective_package(old, old) and old['package'] == PACKAGE,
            'invalid Node.js effective package identity')
    current = selector.effective_package_identity(pkgsrc_root, PACKAGE, old['upstream'])
    require(selector.equivalent_effective_package(old, current),
            'Node.js effective package changed')
    return record


def prepare(archive, output, patch, git, pkgsrc_root=None):
    require(os.path.isabs(patch), 'select an absolute patch executable')
    require(pkgsrc_root is not None or (isinstance(git, str) and os.path.isabs(git)),
            'select absolute Git for checkout export')
    output = Path(output)
    require(output.is_absolute(), 'prepared source output must be absolute')
    output = Path(paths.canonical_existing(output.parent), output.name)
    require(not os.path.lexists(output), 'prepared source output already exists')
    paths.reject_overlap(str(output), str(PORTS))
    owner_sha256 = digest(read(Path(__file__).resolve()))
    identity = source_identity(git) if pkgsrc_root is None else None
    with tempfile.TemporaryDirectory(prefix='.node-source-', dir=output.parent) as tmp:
        tmp = Path(tmp)
        if pkgsrc_root is None:
            exported = tmp / 'pkgsrc'
            process.capture([sys.executable, '-B', str(PORTS / 'scripts/prepare-pkgsrc.py'),
                             str(exported), '--git', git, '--patch', patch],
                            env=process.sanitized_environment())
            upstream = identity['export']['upstream']
        else:
            require(os.path.isabs(pkgsrc_root), 'pkgsrc export must be absolute')
            exported = Path(paths.canonical_existing(pkgsrc_root))
            paths.reject_overlap(str(output), str(exported))
            upstream = read(exported / 'EMBERBSD-PKGSRC-REVISION').decode('ascii').strip()
        selector = identity_module()
        effective = selector.effective_package_identity(exported, PACKAGE, upstream)
        metadata, patches = recipe(exported)
        archive = Path(paths.canonical_existing(archive))
        require(archive.name == metadata['archive'], 'Node.js archive filename differs from recipe')
        data = read(archive)
        hashes = sourceprep.archive_hashes(data)
        require(all(hashes[key] == metadata[key] for key in ('sha512', 'blake2s', 'size')),
                'Node.js archive checksum differs from recipe')
        packed = tmp / archive.name
        packed.write_bytes(data)
        sourceprep.extract_archive(packed, tmp, metadata['distname'], 'Node.js',
                                   max_bytes=2 * 1024 * 1024 * 1024)
        root = tmp / metadata['distname']
        original_backups = {p.relative_to(root) for p in root.rglob('*')
                            if p.name.endswith(('.orig', '.rej'))}
        for index, path in enumerate(patches):
            delta = read(path)
            require(digest(delta) == metadata['recipe']['patches/' + path.name], 'Node.js patch changed')
            sourceprep.apply_patch(patch, path, delta, root, 'Node.js',
                patch_args=('-p0', '-f', '-N', '-F0', '-V', 'none'),
                backup_directory=tmp / ('patch-backups-' + str(index)),
                allow_dev_null=True)
        require({p.relative_to(root) for p in root.rglob('*')
                 if p.name.endswith(('.orig', '.rej'))} == original_backups,
                'Node.js patch left a backup or reject')
        if identity is not None:
            require(identity == source_identity(git), 'pkgsrc export inputs changed during preparation')
        current = selector.effective_package_identity(exported, PACKAGE, upstream)
        require(selector.equivalent_effective_package(effective, current),
                'effective Node.js recipe changed during preparation')
        require(owner_sha256 == digest(read(Path(__file__).resolve())),
                'Node.js source owner changed during preparation')
        scoped = {'effective': effective, 'owner_sha256': owner_sha256}
        record = sourceprep.write_prepared_tree_receipt(root, package=PACKAGE, identity=scoped)
        verify_source(root, exported)
        require(sourceprep.archive_hashes(read(archive)) == hashes, 'Node.js archive changed during preparation')
        publish_directory_noreplace(root, output)
    return record


def main():
    sdk_source.install_signal_handlers()
    args = load_sdk(sys.argv[1:])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--git', help='absolute Git inspector for prepare')
    sub = parser.add_subparsers(dest='action', required=True)
    produce = sub.add_parser('prepare')
    produce.add_argument('--archive', required=True)
    produce.add_argument('--output', required=True)
    produce.add_argument('--patch', required=True)
    produce.add_argument('--pkgsrc-root', help='absolute path to a prepared pkgsrc export')
    check = sub.add_parser('verify-source')
    check.add_argument('--source', required=True)
    check.add_argument('--pkgsrc-root', required=True, help='current prepared pkgsrc export')
    payload = sub.add_parser('verify-payload')
    payload.add_argument('--source', required=True)
    selected = parser.parse_args(args)
    try:
        if selected.action == 'prepare':
            record = prepare(selected.archive, selected.output, selected.patch, selected.git, selected.pkgsrc_root)
        elif selected.action == 'verify-source':
            record = verify_source(selected.source, selected.pkgsrc_root)
        else:
            record = verify_payload(selected.source)
        sys.stdout.buffer.write(jsonio.json_bytes(record))
    except (SDKError, OSError, ValueError) as exc:
        sdk_source.exit_error(exc, 'Node.js source: ')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        sdk_source.exit_error(error, 'Node.js source: ')
