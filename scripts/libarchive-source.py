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


def verify(source, sdk_source, git):
    identity = selected_identity(sdk_source, git)
    from emberbsd_sdk import sourceprep
    return sourceprep.validate_prepared_tree(source, package=PACKAGE, identity=identity)


def prepare(destination, sdk_source, git, patch):
    destination = Path(destination)
    if not destination.is_absolute() or not destination.parent.is_dir() or os.path.lexists(destination):
        raise ValueError('destination must be a new absolute path with an existing parent')
    identity = selected_identity(sdk_source, git)
    from emberbsd_sdk import paths, process, publication, sourceprep
    paths.reject_overlap(str(destination), str(ROOT))
    with tempfile.TemporaryDirectory(prefix='.libarchive-source-', dir=destination.parent) as work:
        work = Path(work)
        export = work / 'pkgsrc'
        command = [sys.executable, '-B', str(ROOT / 'scripts/prepare-pkgsrc.py'),
                   str(export), '--git', git, '--patch', patch]
        subprocess.run(command, check=True, env=process.sanitized_environment(), stdout=sys.stderr)
        payload = work / 'source'
        shutil.copytree(export / PACKAGE / 'files', payload, symlinks=True)
        if selected_identity(sdk_source, git) != identity:
            raise ValueError('Ports export inputs changed during preparation')
        record = sourceprep.write_prepared_tree_receipt(payload, package=PACKAGE, identity=identity)
        sourceprep.validate_prepared_tree(payload, package=PACKAGE, identity=identity)
        publication.publish_directory_noreplace(payload, destination)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('prepare', 'verify'))
    parser.add_argument('source')
    parser.add_argument('--sdk-source', required=True)
    parser.add_argument('--git', required=True)
    parser.add_argument('--patch')
    args = parser.parse_args()
    if args.operation == 'prepare':
        if not args.patch or not os.path.isabs(args.patch):
            parser.error('prepare requires an absolute --patch')
        result = prepare(args.source, args.sdk_source, args.git, args.patch)
    else:
        result = verify(args.source, args.sdk_source, args.git)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
