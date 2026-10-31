#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Prepare the common, fully patched pkgsrc libfetch FILESDIR."""
import argparse
import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import sys
import tempfile

sys.dont_write_bytecode = True
PORTS = Path(__file__).resolve().parents[3]
PACKAGE = 'net/libfetch'
sys.path.insert(0, str(PORTS / 'pkgsrc/lang/llvm/files'))
import sdk_source
sys.path.append(str(PORTS / 'scripts'))
import prepared_receipt


def identity_module():
    spec = importlib.util.spec_from_file_location('pkgsrc_source_identity', PORTS / 'scripts/pkgsrc-source-identity.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git_effective_identity(git):
    return identity_module().git_package_identity(PORTS, PACKAGE, git)


def identity(git):
    return {'effective': git_effective_identity(git),
            'owner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}


def require(condition, message):
    if not condition:
        raise SDKError(message)


def payload(root):
    return identity_module().material_snapshot(root)


def copy_files(exported, root, expected):
    source = Path(exported) / PACKAGE / 'files'
    require(source.is_dir() and not source.is_symlink(), 'missing common libfetch FILESDIR')
    required = ('common.c', 'common.h', 'fetch.c', 'fetch.h', 'file.c', 'ftp.c',
                'http.c', 'errlist.sh', 'ftp.errors', 'http.errors', 'fetch.3')
    require(all((source / item).is_file() and not (source / item).is_symlink() for item in required),
            'incomplete common libfetch FILESDIR')
    before = payload(source)
    require(before == expected, 'common libfetch FILESDIR changed after export verification')
    shutil.copytree(source, root)
    require(payload(root) == before and payload(source) == before,
            'common libfetch FILESDIR changed during preparation')


def export_tree(tmp, git, patch, shared):
    require(patch and os.path.isabs(patch), 'select an absolute patch tool')
    selected = (identity_module().shared_export(shared, PORTS, git, SDK_SOURCE, patch)
                if shared else None)
    if selected is not None:
        # The receipt identity is the export key: the pinned pkgsrc commit,
        # the overlay inputs and the patch tool that produced this FILESDIR.
        # A matching key selects the export without reading FILESDIR again.
        snapshot = identity_module().shared_export_material(shared, PACKAGE + '/files')
        if snapshot is None:
            snapshot = payload(selected / PACKAGE / 'files')
        return selected, snapshot
    exported = Path(tmp) / 'pkgsrc'
    process.capture([sys.executable, '-B', str(PORTS / 'scripts/prepare-pkgsrc.py'),
                     str(exported), '--git', git, '--patch', patch],
                    env=process.sanitized_environment())
    return exported, payload(exported / PACKAGE / 'files')


def prepare(output, git, patch, shared=None):
    output = Path(output)
    require(output.is_absolute() and output.parent.is_dir() and not os.path.lexists(output),
            'prepared source output must be a new absolute path')
    paths.reject_overlap(str(output), str(PORTS))
    if shared:
        paths.reject_overlap(str(output), str(shared))
    before = identity(git)
    with tempfile.TemporaryDirectory(prefix='.libfetch-source-', dir=output.parent) as tmp:
        exported, expected = export_tree(tmp, git, patch, shared)
        root = Path(tmp) / 'libfetch'
        copy_files(exported, root, expected)
        require(identity(git) == before, 'libfetch recipe changed during preparation')
        record = prepared_receipt.write(root, package=PACKAGE, identity=before)
        publish_directory_noreplace(root, output)
    return record


def verify(source, git, patch, shared=None):
    source = Path(source)
    record = jsonio.read_json(str(source / sourceprep.PREPARED_TREE_RECEIPT))
    old = record.get('identity') if isinstance(record, dict) else None
    record = sourceprep.validate_prepared_tree(source, package=PACKAGE, identity=old)
    current = identity(git)
    if identity_module().current_git_package(old, current['owner_sha256'], lambda: current['effective']):
        # The Git key already covers files/; a matched key does not reread the export.
        if shared:
            identity_module().shared_export(shared, PORTS, git, SDK_SOURCE, patch)
        return record
    require(patch and os.path.isabs(patch), 'changed libfetch identity requires an explicit patch tool')
    with tempfile.TemporaryDirectory(prefix='.libfetch-verify-') as tmp:
        expected = prepare(Path(tmp) / 'expected', git, patch, shared)
        require(identity(git) == current, 'libfetch recipe changed during verification')
        require(expected['tree_sha256'] == record['tree_sha256'], 'prepared libfetch differs from current source')
    return record


def main():
    sdk_source.install_signal_handlers()
    args = sdk_source.load_sdk(sys.argv[1:])
    sdk, args = args
    global SDK_SOURCE, jsonio, paths, process, sourceprep, SDKError, publish_directory_noreplace
    SDK_SOURCE = sdk
    from emberbsd_sdk import jsonio, paths, process, sourceprep
    from emberbsd_sdk.errors import SDKError
    from emberbsd_sdk.publication import publish_directory_noreplace
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--git', required=True)
    sub = parser.add_subparsers(dest='action', required=True)
    prep = sub.add_parser('prepare')
    prep.add_argument('--output', required=True)
    prep.add_argument('--patch', required=True)
    prep.add_argument('--scoped-identity', action='store_true')
    prep.add_argument('--pkgsrc-export')
    check = sub.add_parser('verify-source')
    check.add_argument('--source', required=True)
    check.add_argument('--patch')
    check.add_argument('--pkgsrc-export')
    selected = parser.parse_args(args)
    try:
        if selected.action == 'prepare':
            record = prepare(selected.output, selected.git, selected.patch, selected.pkgsrc_export)
        else:
            record = verify(selected.source, selected.git, selected.patch, selected.pkgsrc_export)
        sys.stdout.buffer.write(jsonio.json_bytes(record))
    except (SDKError, OSError, ValueError) as exc:
        sdk_source.exit_error(exc, 'libfetch source: ')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        sdk_source.exit_error(error, 'libfetch source: ')
