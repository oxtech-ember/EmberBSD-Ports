#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Exercise the actual archive writer against explicit target OS fixtures."""

import argparse
from contextlib import contextmanager
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import shutil

sys.dont_write_bytecode = True
import tempfile
from unittest.mock import patch
import zipfile


class ArchiveSelectionError(AssertionError):
    pass


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@contextmanager
def in_directory(path):
    original = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(original)


def fixture(path, kind):
    files = {
        'LICENSE': b'electron-license\n',
        'LICENSES.chromium.html': b'chromium-licenses\n',
        'version': b'44.9.3\n',
        'resources/default_app.asar': b'asar-data',
        'locales/en-US.pak': b'locale-data',
        'debug/symbols.debug': b'excluded-debug',
    }
    deps = list(files)
    if kind == 'elf':
        files.update({
            'electron': b'original-electron',
            'electron.stripped': b'stripped-electron',
            'chrome_sandbox': b'original-sandbox',
            'chrome_sandbox.stripped': b'stripped-sandbox',
            'libffmpeg.so': b'original-ffmpeg',
            'libffmpeg.so.stripped': b'stripped-ffmpeg',
        })
        deps += ['./electron', 'electron.stripped', './chrome_sandbox',
                 'chrome_sandbox.stripped', './libffmpeg.so',
                 'libffmpeg.so.stripped']
    elif kind == 'mac':
        files['Electron.app/Contents/MacOS/Electron'] = b'mac-executable'
        deps += ['Electron.app']
    elif kind == 'win':
        files.update({'electron.exe': b'win-executable', 'ffmpeg.dll': b'win-ffmpeg',
                      'electron.pdb': b'excluded-pdb'})
        deps += ['electron.exe', 'ffmpeg.dll', 'electron.pdb']
    for name, data in files.items():
        target = path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        target.chmod(0o755 if name.startswith(('electron', 'chrome_sandbox')) else 0o644)
    (path / 'runtime_deps.txt').write_text('\n'.join(deps) + '\n')


def exercise(module, path, host, target, kind, flatten=False):
    fixture(path, kind)
    calls = []
    def execute(argv):
        calls.append(list(argv))
        return b''
    with in_directory(path), patch.object(module.sys, 'platform', host), patch.object(module, 'execute', execute):
        module.main(['electron.zip', 'runtime_deps.txt', 'x64', target,
                     'true' if flatten else 'false', ''])
    if calls:
        return {'method': 'external-zip',
                'argv_prefix': calls[0][:4],
                'files': sorted(calls[0][4:])}
    archive = path / 'electron.zip'
    with zipfile.ZipFile(archive) as zipped:
        contents = {}
        for item in zipped.infolist():
            if item.filename in contents:
                raise AssertionError('Duplicate archive member: ' + item.filename)
            contents[item.filename] = {
                'data_hex': zipped.read(item.filename).hex(),
                'mode': item.external_attr >> 16,
                'create_system': item.create_system,
                'compression': item.compress_type,
            }
    return {'method': 'python-zipfile', 'contents': contents}


def require_elf_target(result):
    if result['method'] != 'python-zipfile':
        raise ArchiveSelectionError('ELF cross target used the macOS bundle zip path')
    contents = result['contents']
    expected = {
        'electron': b'stripped-electron',
        'chrome-sandbox': b'stripped-sandbox',
        'libffmpeg.so': b'stripped-ffmpeg',
        'LICENSE': b'electron-license\n',
        'LICENSES.chromium.html': b'chromium-licenses\n',
        'version': b'44.9.3\n',
        'resources/default_app.asar': b'asar-data',
        'locales/en-US.pak': b'locale-data',
    }
    if set(contents) != set(expected):
        raise ArchiveSelectionError('Incorrect ELF archive names: ' + repr(sorted(contents)))
    for name, data in expected.items():
        if contents[name]['data_hex'] != data.hex():
            raise ArchiveSelectionError('Incorrect payload: ' + name)
    if contents['electron']['mode'] & 0o111 != 0o111:
        raise ArchiveSelectionError('Executable mode was not preserved')


def exercise_cases(before_path, after_path, output):
    before = load(before_path.resolve(), 'electron_zip_before')
    after = load(after_path.resolve(), 'electron_zip_after')
    report = {'source_hashes': {name: hashlib.sha256(path.read_bytes()).hexdigest()
                               for name, path in [('before', before_path), ('after', after_path)]},
              'cases': []}
    with tempfile.TemporaryDirectory(prefix='fixtures-', dir=output.resolve().parent) as root_name:
        root = Path(root_name)
        report['temporary_fixture_root'] = str(root)
        def run(module, name, host, target, kind, flatten=False):
            path = root / name
            path.mkdir()
            result = exercise(module, path, host, target, kind, flatten)
            report['cases'].append({'name': name, 'host': host, 'target': target,
                                    'flatten': flatten, 'result': result})
            return result
        bad = run(before, 'before-cross-mac-netbsd', 'darwin', 'netbsd', 'elf')
        if bad['method'] != 'external-zip':
            raise AssertionError('Baseline no longer reproduces the host policy')
        for name in ('./electron', 'electron.stripped', './chrome_sandbox', 'chrome_sandbox.stripped'):
            if name not in bad['files']:
                raise AssertionError('Baseline no longer retains duplicate payload: ' + name)
        try:
            require_elf_target(bad)
        except ArchiveSelectionError as error:
            report['causal_rejection'] = str(error)
        else:
            raise AssertionError('Faulty baseline satisfied the ELF target contract')
        for host in ('darwin', 'linux', 'win32'):
            require_elf_target(run(after, 'after-' + host + '-netbsd', host, 'netbsd', 'elf'))
        for target in ('freebsd', 'openbsd'):
            require_elf_target(run(after, 'after-mac-' + target, 'darwin', target, 'elf'))
        for name, host, target, kind, flatten in (
            ('native-linux', 'linux', 'linux', 'elf', False),
            ('native-mac', 'darwin', 'mac', 'mac', False),
            ('native-win', 'win32', 'win', 'win', False),
            ('native-mac-flatten', 'darwin', 'mac', 'mac', True),
        ):
            old = run(before, 'before-' + name, host, target, kind, flatten)
            new = run(after, 'after-' + name, host, target, kind, flatten)
            if old != new:
                raise AssertionError('Native archive behavior changed: ' + name)
    if root.exists():
        raise AssertionError('Temporary fixture root remains after cleanup')
    report['fixtures_removed'] = True
    report['status'] = 'PASS'
    report['fixture_count'] = len(report['cases'])
    report['limits'] = 'Filesystem fixtures execute the real Python writer. The external macOS zip argv is captured rather than executed. No release target, native prefix, sysroot, or device is used.'
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'status': report['status'], 'fixture_count': report['fixture_count'], 'causal_rejection': report['causal_rejection']}))


def main():
    if sys.implementation.name != 'cpython' or sys.version_info[:2] != (3, 15):
        raise SystemExit('use the selected host CPython 3.15')
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('sdk-source', 'electron-source', 'patch', 'work-dir'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    if any(not path.is_absolute() for path in vars(args).values()):
        parser.error('all paths must be absolute')
    sdk, electron, candidate = (path.resolve(strict=True) for path in
                                (args.sdk_source, args.electron_source, args.patch))
    root = args.work_dir.resolve()
    for boundary in (sdk, electron, Path(__file__).resolve().parent):
        if root.is_relative_to(boundary) or boundary.is_relative_to(root):
            parser.error('--work-dir must be separate from source directories')
    if root.exists() or root.is_symlink() or not root.parent.is_dir():
        parser.error('--work-dir must be new and its parent must exist')
    package = sdk / 'src/emberbsd_sdk'
    if not (package / '__init__.py').is_file():
        parser.error('selected SDK source has no emberbsd_sdk API')
    sys.path.insert(0, str(sdk / 'src'))
    import emberbsd_sdk
    from emberbsd_sdk import errors, inventory, jsonio, process
    modules = (emberbsd_sdk, errors, inventory, jsonio, process)
    if type(emberbsd_sdk.API_VERSION) is not int or emberbsd_sdk.API_VERSION != 1:
        parser.error('selected SDK must provide integer API version 1')
    for module in modules:
        expected = package / ('__init__.py' if module is emberbsd_sdk else
                              module.__name__.rsplit('.', 1)[1] + '.py')
        if Path(module.__file__).resolve() != expected.resolve(strict=True):
            parser.error('SDK module origin mismatch: ' + module.__name__)
    source = electron / 'build/zip.py'
    if not source.is_file():
        parser.error('--electron-source must contain build/zip.py')
    headers = [line for line in candidate.read_text().splitlines()
               if line.startswith(('--- ', '+++ '))]
    if headers != ['--- a/electron/build/zip.py', '+++ b/electron/build/zip.py']:
        parser.error('--patch must modify only electron/build/zip.py with -p1')
    patch_tool = shutil.which('patch', path=process.sanitized_environment()['PATH'])
    if patch_tool is None:
        parser.error('the host patch utility is required')
    patch_tool = Path(patch_tool).resolve(strict=True)
    executable = Path(sys.executable).resolve(strict=True)
    script = Path(__file__).resolve(strict=True)
    inputs = (source, candidate, patch_tool, executable, script)
    hashes = {str(path): inventory.sha256_file(path) for path in inputs}
    baseline_hash = '05779469c35cddb50bc2e60111a83905ad9fb92f187d8b921666d126c118dc60'
    root.mkdir()
    (root / 'logs').mkdir()
    (root / 'home').mkdir()
    (root / 'tmp').mkdir()
    env = process.sanitized_environment()
    env.update(HOME=str(root / 'home'), TMPDIR=str(root / 'tmp'),
               PYTHONDONTWRITEBYTECODE='1')
    commands = []

    def run(name, argv, cwd):
        argv = list(map(str, argv))
        log = root / 'logs' / (name + '.log')
        code = 0
        try:
            process.run_logged(argv, log, cwd=cwd, env=env)
        except errors.CommandError as error:
            code = error.returncode
        receipt = {'name': name, 'argv': argv, 'cwd': str(cwd),
                   'returncode': code, 'log': str(log),
                   'log_sha256': inventory.sha256_file(log)}
        commands.append(receipt)
        jsonio.write_json(root / 'commands.json', commands, exclusive=False)
        if code:
            raise RuntimeError('command failed; inspect ' + str(log))

    def patch_file(name, data, reverse=False):
        tree = root / name
        target = tree / 'electron/build/zip.py'
        target.parent.mkdir(parents=True)
        target.write_bytes(data)
        argv = [patch_tool, '-f', '-p1', '-F0']
        if reverse:
            argv.append('-R')
        run(name, argv + ['-i', candidate], tree)
        return target

    source_bytes = source.read_bytes()
    state = 'baseline' if hashes[str(source)] == baseline_hash else 'patched'
    if state == 'baseline':
        before = root / 'before.py'
        before.write_bytes(source_bytes)
    else:
        before = patch_file('reverse', source_bytes, reverse=True)
    if inventory.sha256_file(before) != baseline_hash:
        raise AssertionError('source does not recover the pinned baseline')
    after = patch_file('forward', before.read_bytes())
    if state == 'patched' and after.read_bytes() != source_bytes:
        raise AssertionError('forward patch does not reproduce the selected source')
    report_path = root / 'cases.json'
    worker = ("from pathlib import Path; import runpy, sys; "
              "runpy.run_path(sys.argv[1], run_name='zip_fixture_worker')"
              "['exercise_cases'](*(Path(p) for p in sys.argv[2:]))")
    run('archive-cases', [executable, '-B', '-I', '-S', '-c', worker, script,
                          before, after, report_path], root)
    report = jsonio.read_json(report_path)
    if report['status'] != 'PASS' or report['fixture_count'] != 14:
        raise AssertionError('the complete fourteen-case regression did not pass')
    after_hashes = {str(path): inventory.sha256_file(path) for path in inputs}
    if hashes != after_hashes:
        raise AssertionError('a selected input changed during the regression')
    summary = {'status': 'PASS', 'source_state': state, 'python': sys.version,
               'sdk_api_version': emberbsd_sdk.API_VERSION,
               'sdk_module_origins': {module.__name__: str(Path(module.__file__).resolve())
                                      for module in modules},
               'input_hashes_before': hashes, 'input_hashes_after': after_hashes,
               'baseline_sha256': inventory.sha256_file(before),
               'patched_sha256': inventory.sha256_file(after),
               'cases_sha256': inventory.sha256_file(report_path),
               'fixture_count': report['fixture_count'],
               'causal_rejection': report['causal_rejection'],
               'fixtures_removed': report['fixtures_removed'],
               'commands': commands, 'limits': report['limits']}
    jsonio.write_json(root / 'summary.json', summary)
    print(json.dumps({'status': 'PASS', 'fixture_count': 14,
                      'source_state': state, 'summary': str(root / 'summary.json')}))


if __name__ == '__main__':
    main()
