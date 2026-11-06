# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Select the verified common SPIRV-Tools source for Chromium."""
import json
from pathlib import Path


def select(controller, view, options, sdk, native, environment):
    selected = [getattr(options, name, None) for name in ('spirv_source', 'spirv_archive', 'spirv_patch')]
    controls = (getattr(options, 'spirv_pkgsrc_export', None), getattr(options, 'spirv_export_patch', None))
    if not any(selected) and not any(controls):
        return {}
    controller.require(all(selected), 'common SPIRV requires source, archive and selected patch tool')
    source, archive, patch = (Path(path).resolve(strict=True) for path in selected)
    owner = Path(options.ports_source) / 'scripts/source-inputs/spirv-tools/source.py'
    command = [native.tool('python'), '-B', str(owner), '--sdk-source', str(options.sdk_source),
               '--git', controller.git(options.git), 'verify-source', '--source', str(source),
               '--archive', str(archive), '--patch', str(patch)]
    if getattr(options, 'spirv_pkgsrc_export', None):
        command += ['--pkgsrc-export', str(options.spirv_pkgsrc_export)]
    if getattr(options, 'spirv_export_patch', None):
        command += ['--export-patch', str(options.spirv_export_patch)]
    record = json.loads(sdk['process'].capture(command, env=controller.source_environment(environment)).stdout)
    controller.require(record.get('package') == 'parallel/spirv-tools', 'wrong common SPIRV owner')
    selection = view.selection(controller.view, sdk['sourceprep'], source)
    controller.require(selection['tree_sha256'] == record.get('tree_sha256'), 'common SPIRV source identity changed')
    options.spirv_selection = selection
    environment['EMBERBSD_SPIRV_SELECTION'] = json.dumps(selection, sort_keys=True, separators=(',', ':'))
    return {'emberbsd_spirv_source_identity': str(source / sdk['sourceprep'].PREPARED_TREE_RECEIPT)}
