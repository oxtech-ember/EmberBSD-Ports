# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Verify the common source and Chromium-generated recovery amalgamation."""
import ast
import hashlib
import json
from pathlib import Path
import re


def select(controller, view, options, sdk, native, environment):
    require = controller.require
    selected = [getattr(options, name, None) for name in
                ('sqlite_source', 'sqlite_archive', 'sqlite_amalgamation', 'sqlite_patch')]
    controls = (getattr(options, 'sqlite_pkgsrc_export', None), getattr(options, 'sqlite_export_patch', None))
    if not any(selected) and not any(controls):
        return None
    require(all(selected),
            'common SQLite needs source, archive, amalgamation and selected patch tool')
    source, archive, output, patch = (Path(p).resolve(strict=True) for p in selected)
    owner = Path(options.ports_source) / 'scripts/source-inputs/sqlite/source.py'
    command = [native.tool('python'), '-B', str(owner), '--sdk-source', str(options.sdk_source),
               '--git', controller.git(options.git), 'verify-source', '--source', str(source),
               '--archive', str(archive), '--patch', str(patch)]
    if getattr(options, 'sqlite_pkgsrc_export', None):
        command += ['--pkgsrc-export', str(options.sqlite_pkgsrc_export)]
    if getattr(options, 'sqlite_export_patch', None):
        command += ['--export-patch', str(options.sqlite_export_patch)]
    record = json.loads(sdk['process'].capture(command, env=controller.source_environment(environment)).stdout)
    selection, receipt = view.selection(controller.view, output)
    identity = receipt['identity']
    require(record.get('package') == 'databases/sqlite3' and
            re.fullmatch(r'[0-9a-f]{64}', record.get('tree_sha256', '')) and
            identity.get('source') == str(source) and identity.get('tree') == record['tree_sha256'],
            'SQLite amalgamation source differs from verified common source')
    chromium = options.workspace / 'src/third_party/sqlite'
    inputs = {'common_gni_sha256': chromium / 'sqlite_common_configuration_flags.gni',
              'chromium_gni_sha256': chromium / 'sqlite_chromium_configuration_flags.gni',
              'dev_gni_sha256': chromium / 'sqlite_dev_configuration_flags.gni',
              'extractor_sha256': chromium / 'scripts/extract_sqlite_api.py',
              'generator_sha256': Path(options.ports_source) / 'scripts/source-inputs/sqlite/generate-chromium.py'}
    for key, path in inputs.items():
        require(identity.get(key) == hashlib.sha256(path.read_bytes()).hexdigest(),
                'SQLite generator input changed: ' + key)
    flags = []
    common_flags = []
    for key, variable in (('common_gni_sha256', 'sqlite_common_configuration_flags'),
                          ('chromium_gni_sha256', 'sqlite_chromium_configuration_flags')):
        tree = ast.parse(inputs[key].read_text())
        rows = [ast.literal_eval(item.value) for item in tree.body if isinstance(item, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == variable for target in item.targets)]
        require(len(rows) == 1 and isinstance(rows[0], list) and
                all(isinstance(flag, str) and re.fullmatch(r'SQLITE_[A-Z0-9_]+(?:=[A-Za-z0-9_,.-]+)?', flag)
                    for flag in rows[0]), 'invalid SQLite Chromium flag list')
        flags.extend(rows[0])
        if key == 'common_gni_sha256':
            common_flags = list(rows[0])
    require(identity.get('flags') == flags and all(item in flags for item in
            ('SQLITE_HAVE_SQLITE3R', 'SQLITE_OMIT_LOAD_EXTENSION', 'SQLITE_SECURE_DELETE')),
            'SQLite Chromium policy differs from selected inputs')
    tree = ast.parse(inputs['dev_gni_sha256'].read_text())
    rows = [ast.literal_eval(item.value) for item in tree.body if isinstance(item, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == 'sqlite_dev_configuration_flags'
                    for target in item.targets)]
    require(len(rows) == 1 and isinstance(rows[0], list) and
            all(isinstance(flag, str) and re.fullmatch(r'SQLITE_[A-Z0-9_]+(?:=[A-Za-z0-9_,.-]+)?', flag)
                for flag in rows[0]) and identity.get('dev_flags') == common_flags + rows[0],
            'SQLite developer policy differs from selected inputs')
    environment['EMBERBSD_SQLITE_SELECTION'] = json.dumps(selection, sort_keys=True, separators=(',', ':'))
    options.sqlite_selection = selection
    return selection
