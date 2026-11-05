#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Prepare and verify the common pkgsrc LiteRT source."""
import argparse
import hashlib
from functools import partial
import importlib.util
import os
from pathlib import Path
import re
import sys
import tempfile
from types import SimpleNamespace

sys.dont_write_bytecode = True
PORTS = Path(__file__).resolve().parents[3]
PACKAGE = 'devel/litert'
LABEL = 'LiteRT'
MAX_EXTRACTED_BYTES = 512 * 1024 * 1024
sys.path.insert(0, str(PORTS / 'pkgsrc/lang/llvm/files'))
import sdk_source
sys.path.insert(0, str(PORTS / 'scripts/source-inputs/common'))
import tar_archive
sys.path.append(str(PORTS / 'scripts'))
import prepared_receipt


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


def git_effective_identity(git):
    return identity_module().git_package_identity(PORTS, PACKAGE, git)


def owner_digest():
    return digest(hashlib.sha256(Path(__file__).resolve().read_bytes()).digest() +
                  hashlib.sha256(Path(tar_archive.__file__).resolve().read_bytes()).digest())


def source_identity(git):
    module = identity_module()
    return {'export': module.identity(PORTS, PACKAGE, git, SDK_SOURCE),
            'owner_sha256': owner_digest()}


def recipe(exported):
    recipe_root = Path(exported) / PACKAGE
    common = read(recipe_root / 'Makefile')
    matches = re.findall(rb'^DISTNAME=\s*LiteRT-([0-9]+(?:\.[0-9]+)+)$', common, re.M)
    require(len(matches) == 1, 'ambiguous LiteRT release')
    distname = 'LiteRT-' + matches[0].decode('ascii')
    archive = distname + '.tar.gz'
    info = read(recipe_root / 'distinfo').decode('utf-8')
    hashes = {}
    for label, key in (('SHA512', 'sha512'), ('BLAKE2s', 'blake2s'), ('Size', 'size')):
        values = re.findall(r'^' + label + r' \(' + re.escape(archive) + r'\) = (\S+)(?: bytes)?$', info, re.M)
        require(len(values) == 1, 'ambiguous LiteRT archive ' + label)
        hashes[key] = int(values[0]) if key == 'size' else values[0]
    declared = re.findall(r'^SHA1 \((patch-[^)]+)\) = ([0-9a-f]{40})$', info, re.M)
    patches = sorted((recipe_root / 'patches').glob('patch-*'))
    require([p.name for p in patches] == sorted(name for name, _ in declared),
            'LiteRT patch inventory differs from distinfo')
    for name, expected in declared:
        data = read(recipe_root / 'patches' / name)
        filtered = b''.join(line for line in data.splitlines(keepends=True) if b'$NetBSD' not in line)
        require(hashlib.sha1(filtered).hexdigest() == expected, 'LiteRT patch checksum differs: ' + name)
    inputs = [recipe_root / 'Makefile', recipe_root / 'distinfo', *patches]
    identity = dict(distname=distname, archive=archive, **hashes,
                    recipe={str(path.relative_to(recipe_root)): digest(read(path)) for path in inputs})
    return identity, patches


def source_context():
    """Set LiteRT's archive limit without changing the shared SDK API."""
    facade = SimpleNamespace(
        PREPARED_TREE_RECEIPT=sourceprep.PREPARED_TREE_RECEIPT,
        validate_prepared_tree=sourceprep.validate_prepared_tree,
        archive_hashes=sourceprep.archive_hashes,
        apply_patch=sourceprep.apply_patch,
        extract_archive=partial(sourceprep.extract_archive, max_bytes=MAX_EXTRACTED_BYTES))
    return SimpleNamespace(**{**globals(), 'sourceprep': facade})


def verify(source, git, archive=None, patch=None, pkgsrc_export=None, export_patch=None):
    return tar_archive.verify(source_context(), source, git, archive, patch, pkgsrc_export, export_patch)


def prepare(archive, output, patch, git, scoped_identity=False, exported=None):
    return tar_archive.prepare(source_context(), archive, output, patch, git,
                               scoped_identity, exported)


def shared_tree(selected):
    return tar_archive.shared_tree(source_context(), selected)


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
    produce.add_argument('--pkgsrc-export', help='shared export from scripts/pkgsrc-shared-export.py')
    produce.add_argument('--export-patch', help='patch used to create the shared export')
    check = sub.add_parser('verify-source')
    check.add_argument('--source', required=True)
    check.add_argument('--archive')
    check.add_argument('--patch')
    check.add_argument('--pkgsrc-export', help='shared export from scripts/pkgsrc-shared-export.py')
    check.add_argument('--export-patch', help='patch used to create the shared export')
    selected = parser.parse_args(args)
    try:
        if selected.action == 'prepare':
            record = prepare(selected.archive, selected.output, selected.patch, selected.git, selected.scoped_identity,
                             exported=shared_tree(selected))
        else:
            record = verify(selected.source, selected.git, selected.archive, selected.patch, pkgsrc_export=selected.pkgsrc_export, export_patch=getattr(selected, 'export_patch', None))
        sys.stdout.buffer.write(jsonio.json_bytes(record))
    except (SDKError, OSError, ValueError) as exc:
        sdk_source.exit_error(exc, f'{LABEL} source: ')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        sdk_source.exit_error(error, f'{LABEL} source: ')
