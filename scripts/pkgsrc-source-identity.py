# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Fingerprint the inputs to the canonical pkgsrc export.

The deliberately conservative identity includes every configured overlay.  A
change to an unrelated overlay may require re-preparing a source tree, while
an unrelated commit which leaves these inputs unchanged does not.
"""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys

sys.dont_write_bytecode = True


def effective_package_identity(exported, package, upstream):
    """Describe the effective exported recipe; retain upstream as provenance.

    Callers must supply an export produced by the canonical exporter.  The
    compatibility digest covers the effective recipe, distinfo, patches and
    auxiliary files after all overlays.  The upstream
    revision identifies where it came from but is not part of the digest.
    """
    from emberbsd_sdk import inventory

    root = Path(exported).resolve(strict=True)
    if not isinstance(package, str) or re.fullmatch(
            r'[a-z0-9][a-z0-9+_.-]*/[a-z0-9][a-z0-9+_.-]*', package) is None:
        raise ValueError('invalid package path')
    parts = package.split('/')
    if not isinstance(upstream, str) or len(upstream) != 40 or any(c not in '0123456789abcdef' for c in upstream):
        raise ValueError('invalid upstream revision')
    directory = root.joinpath(*parts)
    if not directory.is_dir() or directory.is_symlink():
        raise ValueError('effective package is not a directory')
    # The preparation owners consume recipe files and the complete patch and
    # files trees.  Descriptions, package manifests, tests and bootstrap
    # metadata are not inputs to those owners' source preparation.
    inputs = ('Makefile', 'Makefile.common', 'distinfo', 'patches', 'files')
    exclude = [child.name for child in directory.iterdir()
               if child.name not in inputs and not child.name.endswith('.mk')]
    rows = inventory.snapshot_tree(str(directory), exclude=exclude)
    payload = {'api': 1, 'package': package, 'tree': rows}
    encoded = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()
    return {'api': 1, 'package': package,
            'effective_package_sha256': hashlib.sha256(encoded).hexdigest(),
            'upstream': upstream}


def equivalent_effective_package(left, right):
    """Compare effective inputs while leaving the recorded origin untouched."""
    keys = {'api', 'package', 'effective_package_sha256', 'upstream'}
    def valid(value):
        return (isinstance(value, dict) and set(value) == keys and
                type(value['api']) is int and value['api'] == 1 and
                isinstance(value['package'], str) and
                re.fullmatch(r'[a-z0-9][a-z0-9+_.-]*/[a-z0-9][a-z0-9+_.-]*', value['package']) is not None and
                isinstance(value['effective_package_sha256'], str) and
                re.fullmatch(r'[0-9a-f]{64}', value['effective_package_sha256']) is not None and
                isinstance(value['upstream'], str) and
                re.fullmatch(r'[0-9a-f]{40}', value['upstream']) is not None)
    return (valid(left) and valid(right) and left['package'] == right['package'] and
            left['effective_package_sha256'] == right['effective_package_sha256'])


def identity(ports_root, package, git, sdk_source):
    root, package, payload, _ = export_inputs(ports_root, git, sdk_source, package)
    payload['package'] = package
    encoded = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()
    return {'api': 1, 'package': package,
            'export_inputs_sha256': hashlib.sha256(encoded).hexdigest(),
            'upstream': payload['upstream']}


def export_inputs(ports_root, git, sdk_source, package=None):
    """Return the package-independent inputs of the canonical export."""
    root = Path(ports_root).resolve(strict=True)
    if not os.path.isabs(str(git)) or not os.path.isfile(git) or not os.access(git, os.X_OK):
        raise ValueError('git must be an absolute executable')
    loader_path = root / 'pkgsrc/lang/llvm/files/sdk_source.py'
    loader_spec = importlib.util.spec_from_file_location('selected_sdk_source', loader_path)
    loader = importlib.util.module_from_spec(loader_spec)
    loader_spec.loader.exec_module(loader)
    loader.load_sdk(['--sdk-source', str(sdk_source)])
    from emberbsd_sdk import inventory, process, sourceprep

    if sourceprep.PREPARED_TREE_API != 1:
        raise ValueError('SDK prepared-tree API 1 is required')
    path = root / 'scripts/prepare-pkgsrc.py'
    spec = importlib.util.spec_from_file_location('emberbsd_pkgsrc_export', path)
    exporter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(exporter)
    if package is not None:
        package = exporter.package_path(package, 'package')
    recipes, patches, files, _, manifests = exporter.configuration(root, include_manifests=True)

    def run(directory, *args):
        return subprocess.check_output([str(git), '-C', str(directory), *args],
                                       env=process.sanitized_environment()).strip()

    pin = run(root, 'ls-files', '--stage', '--', 'upstream/pkgsrc').split()
    if len(pin) != 4 or pin[0] != b'160000' or pin[2] != b'0':
        raise ValueError('Expected one pinned pkgsrc gitlink')
    if run(root / 'upstream/pkgsrc', 'rev-parse', 'HEAD') != pin[1]:
        raise ValueError('pkgsrc checkout differs from its gitlink')

    inputs = {path, root / 'pkgsrc/export.conf', root / 'pkgsrc/replaces'}
    inputs.update(source for _, source, _, _ in patches)
    inputs.update(source for source, _ in files)
    inputs.update(manifests)
    inputs = {str(p.relative_to(root)): inventory.sha256_file(str(p))
              for p in sorted(inputs) if p.exists()}
    def tree(source):
        rows = inventory.snapshot_installed_tree(str(source))
        for relative, row in rows.items():
            if row['kind'] == 'link':
                target = (source / relative).resolve(strict=True)
                if not target.is_relative_to(root) or not target.is_file():
                    raise ValueError(f'unsupported export source link: {source / relative}')
                row['target_sha256'] = inventory.sha256_file(str(target))
        return rows

    trees = {str(source.relative_to(root)): tree(source) for _, source in recipes}
    # Include overlay category metadata and replacement-list state as well.
    trees['pkgsrc'] = tree(root / 'pkgsrc')
    payload = {'api': 1, 'upstream': pin[1].decode('ascii'),
               'files': inputs, 'trees': trees}
    return root, package, payload, run


SHARED_EXPORT_RECEIPT = 'pkgsrc-export.json'
SHARED_EXPORT_FORMAT = 'emberbsd-pkgsrc-shared-export'


def export_identity(ports_root, git, sdk_source, patch):
    """Identify one canonical export for every package of a run.

    The export depends on the Ports commit, the pinned pkgsrc commit, the
    overlay inputs (which also cover uncommitted overlay edits) and the patch
    tool that applied the infrastructure patches.
    """
    if not os.path.isabs(str(patch)) or not os.path.isfile(patch) or not os.access(patch, os.X_OK):
        raise ValueError('patch must be an absolute executable')
    root, _, payload, run = export_inputs(ports_root, git, sdk_source)
    from emberbsd_sdk import inventory
    encoded = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()
    return {'api': 1, 'ports_commit': run(root, 'rev-parse', 'HEAD').decode('ascii'),
            'upstream': payload['upstream'],
            'export_inputs_sha256': hashlib.sha256(encoded).hexdigest(),
            'patch': {'path': str(patch), 'sha256': inventory.sha256_file(str(patch))}}


def create_shared_export(directory, ports_root, git, sdk_source, patch):
    """Export pkgsrc once into a new directory and record its identity."""
    directory = Path(directory)
    if not directory.is_absolute():
        raise ValueError('shared export directory must be absolute')
    before = export_identity(ports_root, git, sdk_source, patch)
    directory.mkdir(mode=0o700)
    from emberbsd_sdk import process
    subprocess.run([sys.executable, '-B', str(Path(ports_root) / 'scripts/prepare-pkgsrc.py'),
                    str(directory / 'pkgsrc'), '--git', str(git), '--patch', str(patch)],
                   check=True, env=process.sanitized_environment(), stdout=sys.stderr)
    if export_identity(ports_root, git, sdk_source, patch) != before:
        raise ValueError('pkgsrc export inputs changed during the shared export')
    receipt = {'format': SHARED_EXPORT_FORMAT, 'version': 1, 'identity': before}
    with open(directory / SHARED_EXPORT_RECEIPT, 'x', encoding='ascii') as output:
        output.write(json.dumps(receipt, sort_keys=True) + '\n')
    return receipt


def shared_export(directory, ports_root, git, sdk_source, patch):
    """Return the pkgsrc tree of a shared export made from current inputs.

    The caller owns the directory for the duration of its run; this check
    binds the export to the Ports commit, pkgsrc commit, overlay inputs and
    patch tool selected now, and refuses an export made from other ones.
    """
    directory = Path(directory)
    if not directory.is_absolute() or directory.is_symlink() or not directory.is_dir():
        raise ValueError('shared pkgsrc export must be an absolute real directory')
    path = directory / SHARED_EXPORT_RECEIPT
    if path.is_symlink() or not path.is_file():
        raise ValueError('shared pkgsrc export has no receipt')
    receipt = json.loads(path.read_text(encoding='ascii'))
    if (not isinstance(receipt, dict) or set(receipt) != {'format', 'version', 'identity'} or
            receipt['format'] != SHARED_EXPORT_FORMAT or type(receipt['version']) is not int or
            receipt['version'] != 1):
        raise ValueError('invalid shared pkgsrc export receipt')
    if receipt['identity'] != export_identity(ports_root, git, sdk_source, patch):
        raise ValueError('shared pkgsrc export was made from different inputs')
    exported = directory / 'pkgsrc'
    revision = exported / 'EMBERBSD-PKGSRC-REVISION'
    if (exported.is_symlink() or not exported.is_dir() or revision.is_symlink() or not revision.is_file() or
            revision.read_text(encoding='ascii') != receipt['identity']['upstream'] + '\n'):
        raise ValueError('shared pkgsrc export tree differs from its receipt')
    return exported
