#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Exercise the version action with the selected Node and common semver package."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--node', type=Path, required=True)
parser.add_argument('--semver', type=Path, required=True)
parser.add_argument('--electron', type=Path, required=True)
args = parser.parse_args()
owner = Path(__file__).resolve().parents[1] / 'electron44/files'
with tempfile.TemporaryDirectory() as name:
    root = Path(name).resolve(); local = root / 'owner'; local.mkdir()
    for filename in ('electron-version-provider.py', 'node-providers.py'):
        shutil.copyfile(owner / filename, local / filename)
    prefix = root / 'prefix'; modules = prefix / 'lib/node_modules'
    shutil.copytree(args.semver, modules / 'semver')
    controller = '''from pathlib import Path\nclass Native:\n bundle_root={prefix!r}\n host={{'os':'Darwin','cpu':'arm64'}}\n path={path!r}\n def tool(self, role): return {{'node':{node!r}, 'rollup':self.bundle_root+'/lib/node_modules/rollup/dist/bin/rollup', 'tsc':self.bundle_root+'/lib/node_modules/typescript/bin/tsc'}}[role]\nclass Host:\n def load_host_prefix(self,*a,**k): return Native()\nclass Process:\n def sanitized_environment(self): return {{}}\ndef load_sdk(root): return {{'host_prefix':Host(), 'process':Process()}}\n'''.format(prefix=str(prefix),path=str(args.node.parent),node=str(args.node))
    (local / 'build-electron.py').write_text(controller)
    source = root / 'electron'; (source / 'script').mkdir(parents=True)
    shutil.copyfile(args.electron / 'script/generate-version-json.js', source / 'script/generate-version-json.js')
    manifest = source / 'package.json'; stamp = root / 'stamp'; output = root / 'version.json'
    files = sorted(str(p) for p in (modules / 'semver').rglob('*') if p.is_file())
    command = [os.sys.executable, str(local / 'electron-version-provider.py'), '--sdk-source', str(root),
               '--host-prefix', str(prefix), '--node-provider', str(local / 'node-providers.py'),
               '--node', str(args.node), '--source', str(source / 'script/generate-version-json.js'),
               '--output', str(output), '--stamp', str(stamp), '--version', '45.0.0-beta.2']
    for path in files: command.extend(('--provider-input', path))
    manifest.write_text('{"devDependencies":{"semver":"^7.6.3"}}')
    subprocess.run(command, check=True, capture_output=True)
    assert stamp.exists() and json.loads(output.read_text())['prerelease'] == 'beta.2'
    shadow = source / 'node_modules/semver'; shadow.mkdir(parents=True)
    (shadow / 'index.js').write_text('throw new Error(\"private provider executed\")')
    assert subprocess.run(command, capture_output=True).returncode and not stamp.exists()
    shutil.rmtree(source / 'node_modules')
    stamp.write_text('stale')
    manifest.write_text('{"devDependencies":{"semver":"^6"}}')
    assert subprocess.run(command, capture_output=True).returncode and not stamp.exists()
    manifest.write_text('{"devDependencies":{"semver":"^7"}}'); stamp.write_text('stale')
    (modules / 'semver/index.js').unlink()
    assert subprocess.run(command, capture_output=True).returncode and not stamp.exists()
    print('version provider success, shadow, range and missing-input failures PASS')
