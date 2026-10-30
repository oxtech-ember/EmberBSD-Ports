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
import re
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
    result = selector.identity(ROOT, PACKAGE, git, sdk_source)
    from emberbsd_sdk import inventory
    result['owner_sha256'] = inventory.sha256_file(__file__)
    return result


def verify(source, sdk_source, git, patch=None, pkgsrc_export=None):
    # Check a caller's shared export before any early return: an unchanged
    # Git-identified receipt needs no export, but a broken one must not pass.
    shared = (module(ROOT / 'scripts/pkgsrc-source-identity.py', 'pkgsrc_identity').shared_export(
        pkgsrc_export, ROOT, git, sdk_source, patch) if pkgsrc_export else None)
    identity = selected_identity(sdk_source, git)
    from emberbsd_sdk import jsonio, process, sourceprep
    record = jsonio.read_json(str(Path(source) / sourceprep.PREPARED_TREE_RECEIPT))
    old_identity = record.get('identity') if isinstance(record, dict) else None
    record = sourceprep.validate_prepared_tree(source, package=PACKAGE, identity=old_identity)
    if old_identity == identity:
        return record
    scoped = isinstance(old_identity, dict) and set(old_identity) == {'effective', 'owner_sha256'}
    if scoped and (not isinstance(old_identity['owner_sha256'], str) or
                   re.fullmatch('[0-9a-f]{64}', old_identity['owner_sha256']) is None):
        raise ValueError('invalid scoped libarchive owner identity')
    if not scoped and (set(old_identity) != {'api', 'package', 'export_inputs_sha256', 'upstream', 'owner_sha256'} or
            type(old_identity.get('api')) is not int or old_identity['api'] != 1 or
            old_identity.get('package') != PACKAGE or
            any(not isinstance(old_identity.get(key), str) or re.fullmatch(pattern, old_identity[key]) is None
                for key, pattern in (('export_inputs_sha256', '[0-9a-f]{64}'),
                                     ('upstream', '[0-9a-f]{40}'), ('owner_sha256', '[0-9a-f]{64}')))):
        raise ValueError('unrecognized legacy libarchive identity')
    selector = module(ROOT / 'scripts/pkgsrc-source-identity.py', 'pkgsrc_identity')
    if scoped and selector.current_git_package(old_identity, identity['owner_sha256'],
                                               lambda: selector.git_package_identity(ROOT, PACKAGE, git)):
        # The receipt names the Git objects of the current effective recipe.
        if selected_identity(sdk_source, git) != identity:
            raise ValueError('Ports export inputs changed during verification')
        return record
    if not patch or not os.path.isabs(patch):
        raise ValueError('changed export requires an explicit patch to compare the current libarchive source')
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
            raise ValueError('Ports export inputs changed during verification')
        if scoped:
            selector = module(ROOT / 'scripts/pkgsrc-source-identity.py', 'pkgsrc_identity')
            current = selector.effective_package_identity(export, PACKAGE, identity['upstream'])
            if (not selector.equivalent_effective_package(old_identity['effective'], old_identity['effective']) or
                    old_identity['effective']['package'] != PACKAGE):
                raise ValueError('invalid scoped libarchive package identity')
            changed = (not selector.equivalent_effective_package(old_identity['effective'], current) or
                       old_identity['owner_sha256'] != identity['owner_sha256'])
        if (not scoped or changed) and \
                sourceprep._prepared_tree_digest(export / PACKAGE / 'files') != record['tree_sha256']:
            raise ValueError('prepared libarchive differs from current effective source')
    return record


def prepare(destination, sdk_source, git, patch, scoped_identity=False, pkgsrc_export=None):
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
            export = selector.shared_export(pkgsrc_export, ROOT, git, sdk_source, patch)
        else:
            export = work / 'pkgsrc'
            command = [sys.executable, '-B', str(ROOT / 'scripts/prepare-pkgsrc.py'),
                       str(export), '--git', git, '--patch', patch]
            subprocess.run(command, check=True, env=process.sanitized_environment(), stdout=sys.stderr)
        payload = work / 'source'
        shutil.copytree(export / PACKAGE / 'files', payload, symlinks=True)
        if selected_identity(sdk_source, git) != identity:
            raise ValueError('Ports export inputs changed during preparation')
        if scoped_identity:
            identity = {'effective': selector.git_package_identity(ROOT, PACKAGE, git),
                        'owner_sha256': identity['owner_sha256']}
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
    parser.add_argument('--scoped-identity', action='store_true', help='record effective package identity')
    args = parser.parse_args()
    if args.operation == 'prepare':
        if not args.patch or not os.path.isabs(args.patch):
            parser.error('prepare requires an absolute --patch')
        result = prepare(args.source, args.sdk_source, args.git, args.patch, args.scoped_identity,
                         args.pkgsrc_export)
    else:
        result = verify(args.source, args.sdk_source, args.git, args.patch, args.pkgsrc_export)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
