# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Select the verified common LevelDB source for Chromium."""
import json
from pathlib import Path


def select(controller, view, options, sdk, native, environment):
    selected = [getattr(options, name, None) for name in ('leveldb_source', 'leveldb_archive', 'leveldb_patch')]
    controls = (getattr(options, 'leveldb_pkgsrc_export', None), getattr(options, 'leveldb_export_patch', None))
    if not any(selected) and not any(controls):
        return {}
    controller.require(all(selected), 'common LevelDB requires source, archive and selected patch tool')
    source, archive, patch = (Path(path).resolve(strict=True) for path in selected)
    owner = Path(options.ports_source) / 'scripts/source-inputs/leveldb/source.py'
    command = [native.tool('python'), '-B', str(owner), '--sdk-source', str(options.sdk_source),
               '--git', controller.git(options.git), 'verify-source', '--source', str(source),
               '--archive', str(archive), '--patch', str(patch)]
    if getattr(options, 'leveldb_pkgsrc_export', None):
        command += ['--pkgsrc-export', str(options.leveldb_pkgsrc_export)]
    if getattr(options, 'leveldb_export_patch', None):
        command += ['--export-patch', str(options.leveldb_export_patch)]
    record = json.loads(sdk['process'].capture(command, env=controller.source_environment(environment)).stdout)
    controller.require(record.get('package') == 'databases/leveldb', 'wrong common LevelDB owner')
    selection = view.selection(controller.view, sdk['sourceprep'], source)
    controller.require(selection['tree_sha256'] == record.get('tree_sha256'), 'common LevelDB source identity changed')
    options.leveldb_selection = selection
    environment['EMBERBSD_LEVELDB_SELECTION'] = json.dumps(selection, sort_keys=True, separators=(',', ':'))
    return {'emberbsd_common_leveldb': True,
            'emberbsd_leveldb_identity': str(source / sdk['sourceprep'].PREPARED_TREE_RECEIPT)}
