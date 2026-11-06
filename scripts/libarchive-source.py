#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Prepare or verify the libarchive source from the canonical Ports export."""

import sys
sys.dont_write_bytecode = True

import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / 'scripts'))
import prepared_receipt
PACKAGE = 'archivers/libarchive'


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def selected_identity(sdk_source, git):
    selector = module(ROOT / 'scripts/pkgsrc-source-identity.py', 'pkgsrc_identity')
    from emberbsd_sdk import inventory
    return {'effective': selector.git_package_identity(ROOT, PACKAGE, git),
            'owner_sha256': inventory.sha256_file(__file__)}


def verify(source, sdk_source, git, patch=None, pkgsrc_export=None, export_patch=None):
    # Check a caller's shared export before any early return: an unchanged
    # Git-identified receipt needs no export, but a broken one must not pass.
    shared = (module(ROOT / 'scripts/pkgsrc-source-identity.py', 'pkgsrc_identity').shared_export(
        pkgsrc_export, ROOT, git, sdk_source, export_patch or patch) if pkgsrc_export else None)
    identity = selected_identity(sdk_source, git)
    from emberbsd_sdk import jsonio, process, sourceprep
    record = jsonio.read_json(str(Path(source) / sourceprep.PREPARED_TREE_RECEIPT))
    old_identity = record.get('identity') if isinstance(record, dict) else None
    record = sourceprep.validate_prepared_tree(source, package=PACKAGE, identity=old_identity)
    selector = module(ROOT / 'scripts/pkgsrc-source-identity.py', 'pkgsrc_identity')
    prepared_receipt.require_current_identity(old_identity, PACKAGE)
    if selector.current_git_package(old_identity, identity['owner_sha256'], lambda: identity['effective']):
        if selected_identity(sdk_source, git) != identity:
            raise ValueError('Ports recipe inputs changed during verification')
        return record
    if not patch or not os.path.isabs(patch):
        raise ValueError('changed recipe requires an explicit patch to compare the current libarchive source')
    with tempfile.TemporaryDirectory(prefix='.libarchive-verify-') as work:
        if pkgsrc_export:
            # The run's single export, bound to the current Ports inputs.
            export = shared
        else:
            export = Path(work) / 'pkgsrc'
            command = [sys.executable, '-B', str(ROOT / 'scripts/prepare-pkgsrc.py'),
                       str(export), '--git', git, '--patch', patch]
            subprocess.run(command, check=True, env=process.sanitized_environment(), stdout=sys.stderr)
        if selected_identity(sdk_source, git) != identity:
            raise ValueError('Ports recipe inputs changed during verification')
        if sourceprep._prepared_tree_digest(export / PACKAGE / 'files') != record['tree_sha256']:
            raise ValueError('prepared libarchive differs from current effective source')
    return record


def prepare(destination, sdk_source, git, patch, pkgsrc_export=None, export_patch=None):
    destination = Path(destination)
    if not destination.is_absolute() or not destination.parent.is_dir() or os.path.lexists(destination):
        raise ValueError('destination must be a new absolute path with an existing parent')
    identity = selected_identity(sdk_source, git)
    from emberbsd_sdk import paths, process, publication, sourceprep
    paths.reject_overlap(str(destination), str(ROOT))
    with tempfile.TemporaryDirectory(prefix='.libarchive-source-', dir=destination.parent) as work:
        work = Path(work)
        selector = module(ROOT / 'scripts/pkgsrc-source-identity.py', 'pkgsrc_identity')
        if pkgsrc_export:
            # The run's single export, bound to the current Ports inputs.
            export = selector.shared_export(pkgsrc_export, ROOT, git, sdk_source, export_patch or patch)
        else:
            export = work / 'pkgsrc'
            command = [sys.executable, '-B', str(ROOT / 'scripts/prepare-pkgsrc.py'),
                       str(export), '--git', git, '--patch', patch]
            subprocess.run(command, check=True, env=process.sanitized_environment(), stdout=sys.stderr)
        payload = work / 'source'
        shutil.copytree(export / PACKAGE / 'files', payload, symlinks=True)
        if selected_identity(sdk_source, git) != identity:
            raise ValueError('Ports recipe inputs changed during preparation')
        record = prepared_receipt.write(payload, package=PACKAGE, identity=identity)
        publication.publish_directory_noreplace(payload, destination)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('prepare', 'verify'))
    parser.add_argument('source')
    parser.add_argument('--sdk-source', required=True)
    parser.add_argument('--git', required=True)
    parser.add_argument('--patch')
    parser.add_argument('--pkgsrc-export', help='shared export from scripts/pkgsrc-shared-export.py')
    parser.add_argument('--export-patch', help='patch used to create the shared export')
    args = parser.parse_args()
    loader = module(ROOT / 'pkgsrc/lang/llvm/files/sdk_source.py', 'libarchive_sdk_source')
    loader.load_sdk(['--sdk-source', args.sdk_source])
    if args.operation == 'prepare':
        if not args.patch or not os.path.isabs(args.patch):
            parser.error('prepare requires an absolute --patch')
        result = prepare(args.source, args.sdk_source, args.git, args.patch,
                         args.pkgsrc_export, args.export_patch)
    else:
        result = verify(args.source, args.sdk_source, args.git, args.patch, args.pkgsrc_export, args.export_patch)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
