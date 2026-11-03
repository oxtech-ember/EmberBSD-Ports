#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD contributors (AI-assisted).
"""Type-check Electron's DOM declarations and exercise its ASAR digest helper."""

import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-view', type=Path, required=True,
                    help='prepared Chromium source-view used by the Electron build')
parser.add_argument('--host-prefix', type=Path, required=True,
                    help='selected native prefix containing Python, Node and gpatch')
parser.add_argument('--node', type=Path, required=True,
                    help='selected native Node executable')
parser.add_argument('--diagnostics-dir', type=Path, required=True,
                    help='new local directory for overlays, stamps and action logs')
args = parser.parse_args()

source_view = args.source_view.resolve(strict=True)
prefix = args.host_prefix.resolve(strict=True)
node = args.node.resolve(strict=True)
python = prefix / 'bin/python3.15'
gpatch = prefix / 'bin/gpatch'
ports = Path(__file__).resolve().parents[3]
runner = ports / 'pkgsrc/devel/electron44/files/electron-npm-runner.py'
patch = ports / 'probes/electron/patches/electron-typescript-dom-webcrypto-arraybuffer.patch'
source_src = source_view / 'src'
source_electron = source_src / 'electron'
diagnostics = args.diagnostics_dir.absolute()

if (not source_electron.is_dir() or source_electron.is_symlink() or
        any(not tool.is_file() or not tool.resolve(strict=True).is_relative_to(prefix)
            for tool in (python, node, gpatch)) or
        not runner.is_file() or not patch.is_file()):
    parser.error('prepared source, patch, runner and selected native tools must exist')
if diagnostics.exists() or diagnostics.is_symlink():
    parser.error('diagnostics directory must be new')
if diagnostics.resolve().is_relative_to(source_view):
    parser.error('diagnostics must stay outside the prepared source-view')
diagnostics.mkdir(parents=True)


def link_entry(source, destination):
    destination.symlink_to(source.absolute(), target_is_directory=source.is_dir())


def make_merge_directory(source, destination, copied_names=()):
    destination.mkdir()
    for item in source.iterdir():
        target = destination / item.name
        if item.name in copied_names and item.is_file() and not item.is_symlink():
            shutil.copyfile(item, target)
        else:
            link_entry(item, target)


def make_electron_overlay(source, destination):
    destination.mkdir()
    for item in source.iterdir():
        target = destination / item.name
        if item.name == 'typings' and item.is_dir() and not item.is_symlink():
            make_merge_directory(item, target, {'internal-ambient.d.ts'})
        elif item.name == 'lib' and item.is_dir() and not item.is_symlink():
            target.mkdir()
            for lib_item in item.iterdir():
                lib_target = target / lib_item.name
                if lib_item.name == 'node' and lib_item.is_dir() and not lib_item.is_symlink():
                    make_merge_directory(lib_item, lib_target, {'asar-fs-wrapper.ts'})
                else:
                    link_entry(lib_item, lib_target)
        elif item.is_file() and not item.is_symlink() and (
                item.name == 'package.json' or item.name.startswith('tsconfig')):
            shutil.copyfile(item, target)
        else:
            link_entry(item, target)


def log_action(name, argv, *, cwd, env):
    result = subprocess.run([str(word) for word in argv], cwd=cwd, env=env,
                            capture_output=True, text=True)
    log = diagnostics / (name + '.log')
    log.write_text('argv=' + json.dumps([str(word) for word in argv]) + '\n' +
                   'exit_code=' + str(result.returncode) + '\n' +
                   result.stdout + result.stderr, encoding='utf-8')
    if result.returncode:
        tail = (result.stdout + result.stderr).splitlines()[-80:]
        raise SystemExit(name + ' failed; see ' + str(log) + '\n' + '\n'.join(tail))
    print('PASS: ' + name)


env = {'PATH': str(prefix / 'bin'), 'TMPDIR': str(diagnostics)}
with tempfile.TemporaryDirectory(prefix='electron-ts-overlay-', dir=diagnostics) as temporary:
    overlay_root = Path(temporary) / 'source-view'
    overlay_src = overlay_root / 'src'
    overlay_src.mkdir(parents=True)
    overlay_electron = overlay_src / 'electron'
    for item in source_src.iterdir():
        if item.name == 'electron':
            make_electron_overlay(item, overlay_electron)
        else:
            link_entry(item, overlay_src / item.name)

    applied = subprocess.run([str(gpatch), '-p1', '-d', str(overlay_electron)],
                             input=patch.read_text(encoding='utf-8'), text=True,
                             capture_output=True, env=env)
    if applied.returncode:
        raise SystemExit('source patch failed in temporary overlay:\n' +
                         applied.stdout + applied.stderr)

    log_action(
        'electron-typecheck',
        [python, '-B', runner, '--node', node, '--electron', overlay_electron,
         '--script', 'typecheck', '--', '--project',
         overlay_electron / 'tsconfig.electron.json',
         '--stamp', diagnostics / 'electron-typecheck.stamp'],
        cwd=overlay_electron, env=env)
    log_action(
        'default-app-typecheck',
        [python, '-B', runner, '--node', node, '--electron', overlay_electron,
         '--script', 'tsc', '--', '--project',
         overlay_electron / 'tsconfig.default_app.json', '--skipLibCheck', 'false',
         '--noEmit'],
        cwd=overlay_electron, env=env)

    asar_source = (overlay_electron / 'lib/node/asar-fs-wrapper.ts').read_text(encoding='utf-8')
    matches = re.findall(
        r'const sha256HexAsync = async \(buffer: Uint8Array\) => \{.*?\n\};',
        asar_source, re.DOTALL)
    if len(matches) != 1:
        raise SystemExit('expected exactly one production sha256HexAsync helper')
    helper = matches[0].replace('(buffer: Uint8Array)', '(buffer)', 1)
    node_test = diagnostics / 'asar-digest-buffer-views.js'
    node_test.write_text('''const {Buffer} = require('node:buffer');
const {createHash, webcrypto} = require('node:crypto');
const getCrypto = () => ({webcrypto});
''' + helper + '''
async function check(input, label) {
  const actual = await sha256HexAsync(input);
  const expected = createHash('sha256').update(input).digest('hex');
  if (actual !== expected) throw new Error(label + ' digest differs');
}
async function main() {
  const backing = Buffer.from([99, 1, 2, 3, 4, 88]);
  await check(backing.subarray(1, 5), 'Buffer subview');
  const shared = new SharedArrayBuffer(12);
  const sharedView = new Uint8Array(shared, 3, 5);
  sharedView.set([7, 8, 9, 10, 11]);
  await check(sharedView, 'SharedArrayBuffer view');
  const iterable = new Uint8Array([13, 14, 15]);
  iterable[Symbol.iterator] = function* () { yield 99; yield 98; yield 97; };
  await check(iterable, 'overridden typed-array iterator');
}
main().catch(error => { console.error(error); process.exitCode = 1; });
''', encoding='utf-8')
    log_action('asar-digest-buffer-views', [node, node_test],
               cwd=overlay_electron, env=env)

print('Diagnostics: ' + str(diagnostics))
