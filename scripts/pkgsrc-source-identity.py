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
import subprocess
import sys

sys.dont_write_bytecode = True


def identity(ports_root, package, git, sdk_source):
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
    payload = {'api': 1, 'package': package, 'upstream': pin[1].decode('ascii'),
               'files': inputs, 'trees': trees}
    encoded = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()
    return {'api': 1, 'package': package,
            'export_inputs_sha256': hashlib.sha256(encoded).hexdigest(),
            'upstream': payload['upstream']}
