#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Prepare and verify the pinned NetBSD 11.0 X11 source set (xsrc)."""
import argparse
import hashlib
import os
from pathlib import Path
import sys
import tempfile

sys.dont_write_bytecode = True
PORTS = Path(__file__).resolve().parents[3]
PACKAGE = 'netbsd/xsrc'
# The same archive is pinned by the OS in ember/source.json (x11SourceSha512).
PIN = dict(release='NetBSD-11.0',
           url='https://cdn.netbsd.org/pub/NetBSD/NetBSD-11.0/source/sets/xsrc.tgz',
           archive='xsrc.tgz',
           sha512='c46c9e62d225732b3d8d30d2c5f95b992b434826276f8b66fc04439a309b13e4b751d33366f5c39010f2e309ad70a7bdc7a130fe5ea735792be26ea7c13e2dd5',
           blake2s='b6a9a826867ca377d07648b6a24edd64e6761ce22bdd3a449bb3aec0aa05fc43',
           size=185066186)
# The set stores the tree below usr/xsrc; CVS metadata is recorded as hard links.
ARCHIVE_ROOT, COMPONENT, SKIPPED = 'usr', 'xsrc', ('CVS',)
MAX_MEMBERS, MAX_BYTES = 100000, 1024 ** 3
sys.path.insert(0, str(PORTS / 'pkgsrc/lang/llvm/files'))
import sdk_source


def load_sdk(argv):
    sdk, argv = sdk_source.load_sdk(argv)
    from emberbsd_sdk import jsonio, paths, sourceprep
    from emberbsd_sdk.errors import SDKError
    from emberbsd_sdk.publication import publish_directory_noreplace
    if getattr(sourceprep, 'PREPARED_TREE_API', None) != 1:
        raise SDKError('selected SDK lacks the prepared source tree API')
    if getattr(sourceprep, 'ARCHIVE_SKIP_DIRECTORIES_API', None) != 1:
        raise SDKError('selected SDK cannot skip source set metadata directories')
    globals().update(jsonio=jsonio, paths=paths, sourceprep=sourceprep,
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


def source_identity():
    owner = hashlib.sha256(read(Path(__file__).resolve())).hexdigest()
    return dict(PIN, skipped_directories=list(SKIPPED), owner_sha256=owner)


def verify(source):
    return sourceprep.validate_prepared_tree(source, package=PACKAGE, identity=source_identity())


def prepare(archive, output):
    output = Path(output)
    require(output.is_absolute(), 'prepared source output must be absolute')
    output = Path(paths.canonical_existing(output.parent), output.name)
    require(not os.path.lexists(output), 'prepared source output already exists')
    paths.reject_overlap(str(output), str(PORTS))
    identity = source_identity()
    archive = Path(paths.canonical_existing(archive))
    require(archive.name == PIN['archive'], 'xsrc archive filename differs from the pin')
    data = read(archive)
    hashes = sourceprep.archive_hashes(data)
    require(all(hashes[key] == PIN[key] for key in ('sha512', 'blake2s', 'size')),
            'xsrc archive checksum differs from the pin')
    with tempfile.TemporaryDirectory(prefix='.xsrc-source-', dir=output.parent) as tmp:
        tmp = Path(tmp)
        packed = tmp / archive.name
        packed.write_bytes(data)
        del data
        stage = tmp / 'stage'
        stage.mkdir()
        sourceprep.extract_archive(packed, stage, ARCHIVE_ROOT, 'xsrc', components=(COMPONENT,),
                                   max_members=MAX_MEMBERS, max_bytes=MAX_BYTES,
                                   skip_directories=SKIPPED)
        root = stage / ARCHIVE_ROOT / COMPONENT
        require((root / 'Makefile').is_file() and (root / 'external/mit').is_dir() and
                (root / 'local').is_dir(), 'xsrc archive lacks the X11 source layout')
        require(not any(p.name in SKIPPED for p in root.rglob('*')), 'xsrc metadata directory left in tree')
        require(identity == source_identity(), 'xsrc owner changed during preparation')
        record = sourceprep.write_prepared_tree_receipt(root, package=PACKAGE, identity=identity)
        verify(root)
        require(sourceprep.archive_hashes(read(archive)) == hashes, 'xsrc archive changed during preparation')
        publish_directory_noreplace(root, output)
    return record


def main():
    sdk_source.install_signal_handlers()
    args = load_sdk(sys.argv[1:])
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    produce = sub.add_parser('prepare')
    produce.add_argument('--archive', required=True)
    produce.add_argument('--output', required=True)
    check = sub.add_parser('verify-source')
    check.add_argument('--source', required=True)
    sub.add_parser('pin')
    selected = parser.parse_args(args)
    try:
        if selected.action == 'prepare':
            record = prepare(selected.archive, selected.output)
        elif selected.action == 'verify-source':
            record = verify(selected.source)
        else:
            record = source_identity()
        sys.stdout.buffer.write(jsonio.json_bytes(record))
    except (SDKError, OSError, ValueError) as exc:
        sdk_source.exit_error(exc, 'xsrc source: ')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        sdk_source.exit_error(error, 'xsrc source: ')
