#!/usr/bin/env python3
# Origin: EmberBSD (AI-assisted).
"""Run Electron package.json scripts for GN npm actions without npm.

The EmberBSD source view exposes a scoped electron/node_modules from the
common Ports module prefix.  This runner executes the named package.json
script the way `npm run` does (cwd electron/, node_modules/.bin first on
PATH) with the selected host node, and serves nested `npm run <script>`
through a generated shim.  The pre-flight action checks the scoped build
module set with the packaged pre-flight tool against Electron's ranges.
"""
import argparse
import json
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

# The shared @types/node follows the host Node runtime major used by this
# build; Electron's own typecheck still runs against it.
# Host modules follow host Node 26 and the current registry: @types/node
# tracks host Node; @electron/typescript-definitions 10.0.0 was verified to
# generate electron.d.ts from Electron 45.2.1 docs and pass spec/ts-smoke.
RANGE_DEVIATIONS = {'@types/node': '^26.0.0', '@electron/typescript-definitions': '^10.0.0'}


def fail(message):
    raise SystemExit('electron-npm-runner: ' + message)


def load(electron):
    manifest = json.loads((electron / 'package.json').read_text())
    if manifest.get('name') != '@electron-ci/dev-root':
        fail('not the Electron package.json')
    return manifest


def scoped_modules(electron):
    modules = electron / 'node_modules'
    if not modules.is_dir() or modules.is_symlink():
        fail('electron/node_modules must be the EmberBSD scoped view')
    names = []
    for item in sorted(modules.iterdir()):
        if item.name == '.bin':
            continue
        if item.name.startswith('@'):
            names += [item.name + '/' + sub.name for sub in sorted(item.iterdir())]
        else:
            names.append(item.name)
    return names


def run_script(node, electron, name, args, shim_dir):
    scripts = load(electron).get('scripts', {})
    if name not in scripts:
        fail('package.json has no script ' + name)
    env = {key: value for key, value in os.environ.items() if key != 'PATH'}
    env['PATH'] = os.pathsep.join([str(shim_dir), str(electron / 'node_modules/.bin'),
                                   str(Path(node).parent), '/usr/bin', '/bin'])
    env['npm_lifecycle_event'] = name
    env['npm_package_name'] = '@electron-ci/dev-root'
    command = scripts[name] + ''.join(' ' + shlex.quote(a) for a in args)
    return subprocess.run(['/bin/sh', '-c', command], cwd=electron, env=env).returncode


def write_shim(shim_dir, node, electron):
    shim = shim_dir / 'npm'
    shim.write_text('#!/bin/sh\n'
                    '[ "$1" = run ] && [ $# -ge 2 ] || { echo "npm shim: only npm run <script>" >&2; exit 2; }\n'
                    'shift; s=$1; shift; [ "$1" = -- ] && shift\n'
                    'exec %s %s --node %s --electron %s --script "$s" -- "$@"\n' % (
                        shlex.quote(sys.executable), shlex.quote(str(Path(__file__).resolve())),
                        shlex.quote(node), shlex.quote(str(electron))))
    shim.chmod(0o755)


def pre_flight(node, electron, stamp):
    manifest = load(electron)
    declared = {**manifest.get('dependencies', {}), **manifest.get('devDependencies', {})}
    scoped = {}
    for name in scoped_modules(electron):
        if name not in declared:
            fail('scoped module is not declared by Electron: ' + name)
        scoped[name] = RANGE_DEVIATIONS.get(name, declared[name])
    with tempfile.TemporaryDirectory(prefix='electron-pre-flight-') as tmp:
        root = Path(tmp)
        (root / 'package.json').write_text(json.dumps({'name': 'electron-build-scope', 'private': True,
                                                       'devDependencies': scoped}, indent=2))
        (root / 'node_modules').symlink_to(electron / 'node_modules', target_is_directory=True)
        cli = electron / 'node_modules/pre-flight/lib/cli.js'
        return subprocess.run([node, str(cli), '--directory', str(root), '--stamp', stamp]).returncode


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--node', required=True)
    parser.add_argument('--electron', required=True, type=Path)
    parser.add_argument('--script', required=True)
    parser.add_argument('--stamp')
    parser.add_argument('args', nargs=argparse.REMAINDER)
    options = parser.parse_args()
    args = options.args[1:] if options.args[:1] == ['--'] else options.args
    electron = options.electron.resolve(strict=True)
    if options.script == 'pre-flight':
        if not options.stamp or args:
            fail('pre-flight takes only --stamp')
        return pre_flight(options.node, electron, options.stamp)
    with tempfile.TemporaryDirectory(prefix='electron-npm-') as tmp:
        write_shim(Path(tmp), options.node, electron)
        return run_script(options.node, electron, options.script, args, Path(tmp))


if __name__ == '__main__':
    sys.exit(main())
