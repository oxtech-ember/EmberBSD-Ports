# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Bind Chromium's CLI and declaration inputs to the selected native packages."""
import json
from pathlib import Path


def select(native):
    prefix = Path(native.bundle_root)
    modules = prefix / 'lib/node_modules'
    system = {'Darwin': 'darwin', 'Linux': 'linux', 'NetBSD': 'netbsd'}[native.host['os']]
    machine = {'arm64': 'arm64', 'aarch64': 'arm64', 'x86_64': 'x64', 'amd64': 'x64'}[native.host['cpu']]
    typescript = modules / 'typescript'
    backend = modules / '@typescript' / ('typescript-' + system + '-' + machine)
    rollup = modules / 'rollup'
    for root, expected in ((typescript, 'typescript'),
                           (backend, '@typescript/typescript-' + system + '-' + machine),
                           (rollup, 'rollup')):
        metadata = json.loads((root / 'package.json').read_text())
        if metadata.get('name') != expected:
            raise ValueError('wrong selected Node provider: ' + expected)
    if (json.loads((typescript / 'package.json').read_text())['version'] !=
            json.loads((backend / 'package.json').read_text())['version']):
        raise ValueError('TypeScript entry and native backend versions differ')
    inputs = []
    for root in (typescript, backend, rollup):
        for path in sorted(root.rglob('*')):
            if not path.resolve(strict=True).is_relative_to(prefix):
                raise ValueError('Node provider escapes native prefix')
            if path.is_file():
                inputs.append(str(path))
    definitions = sorted(str(path) for path in (backend / 'lib').glob('*.d.ts'))
    if not definitions or not (backend / 'lib/tsc').is_file():
        raise ValueError('TypeScript native backend or declarations are missing')
    if (Path(native.tool('rollup')).resolve() != rollup / 'dist/bin/rollup' or
            Path(native.tool('tsc')).resolve() != typescript / 'bin/tsc'):
        raise ValueError('selected Node entry differs from its installed common package')
    return dict(environment={'EMBERBSD_HOST_ROLLUP': native.tool('rollup'),
                             'EMBERBSD_HOST_TYPESCRIPT': native.tool('tsc')},
                arguments={'emberbsd_node_provider_inputs': inputs,
                           'emberbsd_typescript_definitions': definitions})
