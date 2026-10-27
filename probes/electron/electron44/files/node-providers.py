# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Bind Chromium's CLI and declaration inputs to the selected native packages."""
import json
from pathlib import Path


def _chromium_tree_tsc(source):
    """Return prepared Chromium bundled tsc when present under source/workspace."""
    if source is None:
        return None
    root = Path(source)
    for relative in ('src/third_party/node/node_modules/typescript/bin/tsc',
                     'third_party/node/node_modules/typescript/bin/tsc'):
        candidate = root / relative
        if not candidate.is_file():
            continue
        package = candidate.resolve(strict=True).parent.parent / 'package.json'
        if not package.is_file():
            continue
        metadata = json.loads(package.read_text())
        if metadata.get('name') == 'typescript':
            return candidate.resolve(strict=True)
    return None


def select(native, source=None):
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
    host_version = json.loads((typescript / 'package.json').read_text())['version']
    if host_version != json.loads((backend / 'package.json').read_text())['version']:
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
    # Host TypeScript 7+ ships lib.dom where HTMLElement.innerHTML is string-only,
    # while Chromium WebUI still assigns string|TrustedHTML (emptyHTML()). Prefer
    # the prepared tree's classic bundled tsc (Chromium pins ~5/6) when present.
    tsc_entry = Path(native.tool('tsc')).resolve()
    host_major = int(host_version.split('.')[0])
    tree_tsc = _chromium_tree_tsc(source)
    if host_major >= 7 and tree_tsc is not None:
        tsc_entry = tree_tsc
    return dict(environment={'EMBERBSD_HOST_ROLLUP': native.tool('rollup'),
                             'EMBERBSD_HOST_TYPESCRIPT': str(tsc_entry)},
                arguments={'emberbsd_node_provider_inputs': inputs,
                           'emberbsd_typescript_definitions': definitions})
