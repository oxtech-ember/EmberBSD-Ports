#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted), not submitted upstream.
"""Run pinned Wayland GN actions with explicit native GN/Ninja/scanner inputs.

Only protocol generation runs. Fixture compiler commands deliberately fail;
this does not validate Chromium compilation, target ABI or the complete graph.
The prepared Chromium Git checkout is read-only; no sync or hooks run.
"""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time


PROBE = Path(__file__).resolve().parents[1]
MEMBERS = tuple('third_party/wayland/' + name for name in
                ('features.gni', 'wayland_protocol.gni',
                 'wayland_scanner_wrapper.py'))
PATCH = PROBE / 'patches/gn-wayland-scanner.patch'


def gn_string(value):
    # GN strings interpolate $, unlike JSON strings.
    return json.dumps(str(value)).replace('$', r'\$')


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'git', 'gn', 'ninja', 'scanner', 'protocol', 'work'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--utility-path', required=True)
    args = parser.parse_args()
    for name in ('source', 'git', 'gn', 'ninja', 'scanner', 'protocol', 'work'):
        if not getattr(args, name).is_absolute():
            parser.error('--' + name + ' must be absolute')
    for name in ('git', 'gn', 'ninja', 'scanner'):
        path = getattr(args, name)
        if not path.is_file() or not os.access(path, os.X_OK):
            parser.error('--' + name + ' must be an executable')
    if args.work.exists() or args.work.resolve().is_relative_to(args.source.resolve()):
        parser.error('--work must be new and outside the source checkout')
    if not all(Path(p).is_absolute() and Path(p).is_dir()
               for p in args.utility_path.split(os.pathsep)):
        parser.error('--utility-path must contain explicit absolute directories')
    if sys.implementation.name != 'cpython' or sys.version_info[:2] != (3, 15):
        parser.error('use selected host CPython 3.15')
    spec = importlib.util.spec_from_file_location(
        'electron_prepare', PROBE / 'electron44/files/prepare-sources.py')
    prepare = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prepare)
    revision = prepare.CHROMIUM_REVISION
    environment = {'PATH': args.utility_path, 'LC_ALL': 'C',
                   'PYTHONDONTWRITEBYTECODE': '1'}
    args.work.mkdir(parents=True)
    logs = args.work / 'logs'
    logs.mkdir()
    commands = []

    def run(name, argv, cwd, error=None):
        result = subprocess.run(list(map(str, argv)), cwd=cwd, env=environment,
                                capture_output=True, text=True, timeout=30)
        output = result.stdout + result.stderr
        (logs / (name + '.log')).write_text(output)
        commands.append({'name': name, 'argv': list(map(str, argv)),
                         'cwd': str(cwd), 'returncode': result.returncode})
        (logs / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        if error is None:
            if result.returncode:
                raise AssertionError(name + ':\n' + output)
        elif result.returncode == 0 or error not in output:
            raise AssertionError(name + ': expected ' + error + '\n' + output)
        return result.stdout

    baseline = args.work / 'baseline'
    for member in MEMBERS:
        target = baseline / member
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(run('read-' + Path(member).name,
            [args.git, '-C', args.source, 'show', revision + ':' + member], args.work))
        if target.read_bytes() != (args.source / member).read_bytes():
            raise AssertionError('prepared source differs from pinned leaf: ' + member)
    before = {member: sha256(args.source / member) for member in MEMBERS}
    patched = args.work / 'patched'
    shutil.copytree(baseline, patched)
    run('patch-check', [args.git, 'apply', '--check', PATCH], patched)
    run('patch-apply', [args.git, 'apply', PATCH], patched)
    tools = args.work / 'selected native tools'
    tools.mkdir()
    selected = tools / 'wayland-scanner'
    shutil.copy2(args.scanner, selected)
    assert sha256(selected) == sha256(args.scanner)
    run('scanner-version', [selected, '--version'], args.work)
    version = (logs / 'scanner-version.log').read_text().strip()
    assert version.startswith('wayland-scanner '), version
    completed = []

    def fixture(name, *, scanner=selected, generator='all', bundled=False,
                original=False, explicit=True):
        root = args.work / name
        shutil.copytree(baseline if original else patched, root)
        (root / '.gn').write_text('buildconfig = "//BUILDCONFIG.gn"\n'
                                 'script_executable = ' + gn_string(sys.executable) + '\n')
        (root / 'BUILDCONFIG.gn').write_text('''
host_toolchain = "//:host"
set_default_toolchain("//:target")
set_defaults("source_set") {
  configs = [ "//build/config/compiler:chromium_code" ]
}
''')
        compiler = root / 'build/config/compiler'
        compiler.mkdir(parents=True)
        (compiler / 'BUILD.gn').write_text('''
config("chromium_code") {}
config("no_chromium_code") {}
''')
        build = '''import("//third_party/wayland/wayland_protocol.gni")
wayland_protocol("protocol") {
  sources = [ "fixture.xml" ]
GENERATOR
}
group("all") { deps = [ ":protocol" ] }
foreach(name, [ "host", "target" ]) {
  toolchain(name) {
    tool("cc") {
      command = "/compiler-must-not-run"
      outputs = [ "{{source_out_dir}}/{{source_name_part}}.o" ]
    }
    tool("stamp") { command = "/stamp-must-not-run" }
  }
}
'''
        build = build.replace('GENERATOR', '' if generator == 'all' else
                              '  generator_type = ' + gn_string(generator))
        (root / 'BUILD.gn').write_text(build)
        shutil.copy2(args.protocol, root / 'fixture.xml')
        wayland = root / 'third_party/wayland'
        (wayland / 'BUILD.gn').write_text('group("wayland_util") {}\n')
        if bundled:
            # Only the default dependency/path contract is tested. This stands
            # in for the bundled C scanner build; it copies a real native tool.
            (root / 'copy-scanner.py').write_text('''import pathlib, shutil, sys
shutil.copy2(sys.argv[1], sys.argv[2])
pathlib.Path(sys.argv[3]).write_text("producer ran\\n")
''')
            with (wayland / 'BUILD.gn').open('a') as out:
                out.write('''action("wayland_scanner") {
  script = "//copy-scanner.py"
  outputs = [ "$root_out_dir/wayland_scanner" ]
  args = [ SCANNER, rebase_path(outputs[0], root_build_dir),
           rebase_path("//producer-ran", root_build_dir) ]
}
'''.replace('SCANNER', gn_string(selected)))
        gen = [args.gn, 'gen', root / 'out', '--root=' + str(root)]
        if explicit:
            gen.append('--args=wayland_scanner_executable=' + gn_string(scanner))
        return root, gen

    def describe(root):
        data = json.loads(run(root.name + '-desc', [args.gn, 'desc', root / 'out',
            '//:protocol_gen', '--format=json', '--root=' + str(root)], root))
        assert len(data) == 1
        return next(iter(data.values()))

    def generate(root, data, suffix='build', error=None):
        outputs = [root / p.removeprefix('//') for p in data['outputs']]
        argv = [args.ninja, '-C', root / 'out', '-j1']
        argv += [os.path.relpath(p, root / 'out') for p in outputs]
        log = run(root.name + '-' + suffix, argv, root, error)
        if error is None:
            assert all(p.is_file() and p.stat().st_size > 0 for p in outputs)
        return outputs, log

    for generator, count in (('all', 3), ('protocol-marshalling', 1),
                             ('protocol-client', 2), ('protocol-server', 2)):
        root, gen = fixture('external-' + generator, generator=generator)
        run(root.name + '-gen', gen, root)
        data = describe(root)
        assert data.get('deps', []) == [], data
        assert str(selected) in data['sources'], data
        assert data['args'][-2:] == ['--cmd', str(selected)], data
        outputs, _ = generate(root, data)
        assert len(outputs) == count
        assert not (root / 'producer-ran').exists()
        completed.append(generator + ' explicit native scanner')
        if generator == 'all':
            _, idle = generate(root, data, 'idle')
            assert 'no work to do' in idle
            timestamps = [p.stat().st_mtime_ns for p in outputs]
            time.sleep(1.1)
            os.utime(selected, None)  # Never touch the installed prefix tool.
            _, rebuilt = generate(root, data, 'scanner-changed')
            assert 'no work to do' not in rebuilt
            assert all(p.stat().st_mtime_ns > old for p, old in zip(outputs, timestamps))
            completed.append('scanner executable input triggers regeneration')

    root, gen = fixture('default-bundled', bundled=True, explicit=False)
    run(root.name + '-gen', gen, root)
    data = describe(root)
    assert data['deps'] == ['//third_party/wayland:wayland_scanner(//:host)'], data
    assert data['args'][-2:] == ['--cmd', './host/wayland_scanner'], data
    generate(root, data)
    assert (root / 'producer-ran').read_text() == 'producer ran\n'
    completed.append('empty default retains upstream host dependency and command')

    # Both the pre-change leaf and the empty post-change default require the
    # host scanner target. Only explicit selection removes that dependency.
    for name, original in (('before', True), ('default-no-producer', False)):
        root, gen = fixture(name, original=original, explicit=original)
        run(name + '-gen', gen, root, 'wayland_scanner')
        completed.append(name + ' missing bundled producer refused')
    for name, value in (('relative', 'wayland-scanner'),
                        ('source-relative', '//selected/wayland-scanner')):
        root, gen = fixture(name, scanner=value)
        run(name + '-gen', gen, root, 'must be an absolute native path')
        completed.append(name + ' path refused')
    root, gen = fixture('missing', scanner=tools / 'missing')
    run(root.name + '-gen', gen, root)
    generate(root, describe(root), error='missing and no known rule to make it')
    completed.append('missing explicit scanner refuses without fallback')
    nonexecutable = tools / 'not-executable'
    shutil.copyfile(selected, nonexecutable)
    nonexecutable.chmod(0o644)
    root, gen = fixture('not-executable', scanner=nonexecutable)
    run(root.name + '-gen', gen, root)
    generate(root, describe(root), error='PermissionError')
    completed.append('nonexecutable explicit scanner refuses without fallback')
    assert before == {member: sha256(args.source / member) for member in MEMBERS}
    result = {'status': 'PASS', 'tests': completed, 'chromium_revision': revision,
              'source_sha256': before, 'patch_sha256': sha256(PATCH),
              'scanner_version': version, 'scanner_sha256': sha256(selected),
              'scope': 'real pinned GN/Ninja protocol generation; no compilation, '
                       'target ABI or complete Chromium graph acceptance'}
    (args.work / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
