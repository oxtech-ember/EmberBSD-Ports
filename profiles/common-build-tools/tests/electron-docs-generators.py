#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Run Electron's real docs and declaration generators with common JS packages."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
for name in ('electron', 'modules', 'node', 'typescript', 'work'):
    parser.add_argument('--' + name, type=Path, required=True)
parser.add_argument('--electron-version', required=True)
a = parser.parse_args()
for name in ('electron', 'modules', 'node', 'typescript'):
    path = getattr(a, name)
    if not path.is_absolute() or not path.exists():
        parser.error(name + ' must be an existing absolute path')
if not a.work.is_absolute() or a.work.exists():
    parser.error('work must be a new absolute path')
a.work.mkdir(parents=True)
def check_links(directory):
    root = directory.resolve(strict=True)
    for path in root.rglob('*'):
        if path.is_symlink() and not path.resolve(strict=True).is_relative_to(root):
            raise ValueError('module symlink escapes selected modules: ' + str(path))

check_links(a.modules)
modules = a.work / 'node_modules'
shutil.copytree(a.modules, modules, symlinks=True)
check_links(modules)
typescript = modules / 'typescript'
if typescript.exists():
    parser.error('modules must not already contain a TypeScript provider')
typescript.symlink_to(a.typescript.resolve(strict=True), target_is_directory=True)
electron = a.work / 'electron'
(electron / 'script/lib').mkdir(parents=True)
(electron / 'spec').mkdir()
for name in ('script/create-api-json.mjs', 'script/lib/get-version.js', 'script/lib/utils.js'):
    shutil.copyfile(a.electron / name, electron / name)
shutil.copytree(a.electron / 'spec/ts-smoke', electron / 'spec/ts-smoke')
(electron / 'docs').symlink_to((a.electron / 'docs').resolve(strict=True), target_is_directory=True)
out = a.work / 'out/fixture'; out.mkdir(parents=True)
if not a.electron_version or any(c not in '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.-' for c in a.electron_version):
    parser.error('invalid Electron version')
(out / 'args.gn').write_text('override_electron_version = "' + a.electron_version + '"\n')
env = os.environ.copy(); env.pop('NODE_PATH', None); env.pop('NODE_OPTIONS', None)
env['ELECTRON_OUT_DIR'] = 'fixture'
def run(*argv):
    subprocess.run([str(a.node), *map(str, argv)], env=env, check=True)
run(electron / 'script/create-api-json.mjs')
generated = a.work / 'definitions'
run(modules / '@electron/typescript-definitions/dist/bin.js', '--api', electron / 'electron-api.json', '--outDir', generated)
shutil.copyfile(generated / 'electron.d.ts', electron / 'electron.d.ts')
run(a.typescript / 'bin/tsc', '--project', electron / 'spec/ts-smoke/tsconfig.json')
print('Electron docs, declarations and TypeScript smoke: PASS')
