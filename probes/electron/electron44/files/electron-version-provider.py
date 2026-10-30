#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Run Electron's version generator with its selected common Node provider."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('sdk-source', 'host-prefix', 'node-provider', 'node', 'source', 'output', 'stamp', 'version'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--provider-input', action='append', default=[])
    args = parser.parse_args()
    stamp = Path(args.stamp)
    stamp.unlink(missing_ok=True)
    try:
        here = Path(__file__).resolve().parent
        spec = importlib.util.spec_from_file_location('electron_controller', here / 'build-electron.py')
        controller = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(controller)
        sdk = controller.load_sdk(Path(args.sdk_source))
        native = sdk['host_prefix'].load_host_prefix(Path(args.host_prefix), required_roles=('node',))
        if Path(native.tool('node')).resolve(strict=True) != Path(args.node).resolve(strict=True):
            raise ValueError('selected Node changed; reconfigure')
        provider_path = Path(args.node_provider).resolve(strict=True)
        if provider_path != here / 'node-providers.py':
            raise ValueError('unexpected provider selector')
        spec = importlib.util.spec_from_file_location('electron_node_providers', provider_path)
        providers = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(providers)
        selected_files = providers.select_electron_semver(native)
        if sorted(selected_files) != sorted(args.provider_input):
            raise ValueError('semver provider inputs changed; reconfigure')
        root = Path(native.bundle_root).resolve(strict=True)
        modules = root / 'lib/node_modules'
        script = Path(args.source).resolve(strict=True)
        package = script.parent.parent / 'package.json'
        metadata = json.loads(package.read_text())
        requested = metadata.get('devDependencies', {}).get('semver')
        if not isinstance(requested, str):
            raise ValueError('Electron semver requirement missing')
        env = sdk['process'].sanitized_environment()
        env.update(PATH=native.path, NODE_PATH=str(modules))
        check = "const fs=require('node:fs'); const r=require('node:module').createRequire(process.argv[1]); if (fs.realpathSync(r.resolve('semver')) !== fs.realpathSync(process.argv[2])) process.exit(1); const s=r('semver'); const p=require(process.argv[3]); if (!s.validRange(process.argv[4]) || !s.satisfies(p.version,process.argv[4])) process.exit(1)"
        subprocess.run([native.tool('node'), '-e', check, str(script), str(modules / 'semver/index.js'), str(modules / 'semver/package.json'), requested], env=env, check=True)
        subprocess.run([native.tool('node'), str(script), args.output, args.version], env=env, check=True)
        stamp.parent.mkdir(parents=True, exist_ok=True)
        stamp.write_text('selected-provider-ok\n')
    except BaseException:
        stamp.unlink(missing_ok=True)
        raise


if __name__ == '__main__':
    main()
