# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Bind Chromium's CLI and declaration inputs to the selected native packages."""
import json
import os
import subprocess
from pathlib import Path


def select_ts_proto(modules, prefix):
    ts_proto_names = ('@bufbuild/protobuf', 'case-anything', 'dprint-node',
                      'ts-poet', 'ts-proto', 'ts-proto-descriptors')
    ts_proto_inputs = []
    for name in ts_proto_names:
        root = modules / name
        metadata = json.loads((root / 'package.json').read_text())
        if metadata.get('name') != name or not metadata.get('version'):
            raise ValueError('invalid selected ts-proto provider: ' + name)
        for path in sorted(root.rglob('*')):
            if not path.resolve(strict=True).is_relative_to(prefix):
                raise ValueError('ts-proto provider escapes native prefix')
            if path.is_file():
                ts_proto_inputs.append(str(path))
    if not (modules / 'ts-proto/protoc-gen-ts_proto').is_file() or not (modules / 'dprint-node/dprint-node.node').is_file():
        raise ValueError('selected ts-proto entry or dprint addon is missing')
    return ts_proto_inputs

def select_electron_semver(native):
    prefix = Path(native.bundle_root).resolve(strict=True)
    semver = prefix / 'lib/node_modules/semver'
    metadata = json.loads((semver / 'package.json').read_text())
    if metadata.get('name') != 'semver' or not isinstance(metadata.get('version'), str) or not metadata['version']:
        raise ValueError('invalid selected semver provider')
    inputs = []
    for path in sorted(semver.rglob('*')):
        if not path.resolve(strict=True).is_relative_to(prefix):
            raise ValueError('semver provider escapes native prefix')
        if path.is_file():
            inputs.append(str(path))
    if not (semver / 'index.js').is_file():
        raise ValueError('selected semver entry missing')
    return inputs

def select(native, *, electron=False):
    prefix = Path(native.bundle_root).resolve(strict=True)
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
    esbuild = modules / 'esbuild'
    esbuild_module = esbuild / 'lib/main.js'
    esbuild_metadata = esbuild / 'package.json'
    esbuild_binary = prefix / 'bin/esbuild'
    for path in (esbuild_module, esbuild_metadata, esbuild_binary):
        if not path.is_file() or not path.resolve(strict=True).is_relative_to(prefix):
            raise ValueError('selected esbuild provider is missing or escapes native prefix')
    if not os.access(esbuild_binary, os.X_OK):
        raise ValueError('selected esbuild binary is not executable')
    metadata = json.loads(esbuild_metadata.read_text())
    esbuild_version = metadata.get('version')
    if metadata.get('name') != 'esbuild' or not isinstance(esbuild_version, str) or not esbuild_version or any(ord(c) < 32 for c in esbuild_version):
        raise ValueError('invalid selected esbuild metadata')
    actual = subprocess.check_output([str(esbuild_binary), '--version'], env={'PATH': native.path}, text=True).strip()
    if actual != esbuild_version:
        raise ValueError('selected esbuild binary and JavaScript versions differ')
    lit_names = ('@lit-labs/ssr-dom-shim', '@lit/reactive-element',
                 '@types/trusted-types', 'lit-html', 'lit-element', 'lit')
    lit_versions = []
    lit_inputs = []
    trusted_types_inputs = []
    trusted_types_version = ""
    for name in lit_names:
        root = modules / name
        metadata = json.loads((root / 'package.json').read_text())
        version = metadata.get('version')
        if (metadata.get('name') != name or not isinstance(version, str) or
                not version or any(ord(c) < 32 for c in version)):
            raise ValueError('invalid selected Lit provider: ' + name)
        if name == '@types/trusted-types':
            trusted_types_version = version
        else:
            lit_versions.append(name + '@' + version)
        for path in sorted(root.rglob('*')):
            if not path.resolve(strict=True).is_relative_to(prefix):
                raise ValueError('Lit provider escapes native prefix')
            if path.is_file():
                if name == '@types/trusted-types':
                    trusted_types_inputs.append(str(path))
                else:
                    lit_inputs.append(str(path))
    semver_inputs = select_electron_semver(native) if electron else []
    ts_proto_inputs = select_ts_proto(modules, prefix)
    return dict(environment={'EMBERBSD_HOST_ROLLUP': native.tool('rollup'),
                             'EMBERBSD_HOST_TYPESCRIPT': native.tool('tsc'),
                             'EMBERBSD_TYPESCRIPT_NATIVE_BINARY': str(backend / 'lib/tsc')},
                arguments={'emberbsd_electron_semver_inputs': semver_inputs,
                           'emberbsd_node_modules': str(modules),
                           'emberbsd_ts_proto_inputs': ts_proto_inputs,
                           'emberbsd_lit_versions': lit_versions,
                           'emberbsd_lit_inputs': lit_inputs,
                           'emberbsd_trusted_types_inputs': trusted_types_inputs,
                           'emberbsd_trusted_types_version': trusted_types_version,
                           'emberbsd_devtools_esbuild_module': str(esbuild_module),
                           'emberbsd_devtools_esbuild_binary': str(esbuild_binary),
                           'emberbsd_devtools_esbuild_metadata': str(esbuild_metadata),
                           'emberbsd_devtools_esbuild_version': esbuild_version,
                           'emberbsd_node_provider_inputs': inputs,
                           'emberbsd_typescript_definitions': definitions,
                           'emberbsd_typescript_native_binary': str(backend / 'lib/tsc'),
                           'emberbsd_typescript_host_python': native.tool('python')})
