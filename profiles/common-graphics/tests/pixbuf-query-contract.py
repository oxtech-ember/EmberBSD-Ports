#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Real GCC16 ELF and controlled transport fixtures.
"""Check the production pixbuf helper without running target code or SSH."""

import argparse
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
from types import SimpleNamespace

sys.dont_write_bytecode = True

TARGETS = {
    'aarch64': ('aarch64--netbsd', 183),
    'amd64': ('x86_64--netbsd', 62),
}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def load_sdk(source):
    require(source and os.path.isabs(source), 'set an absolute --sdk-source or EMBERBSD_SDK_SOURCE')
    root = Path(source).resolve(strict=True)
    package = root / 'src/emberbsd_sdk'
    require((package / '__init__.py').is_file(), 'SDK source has no emberbsd_sdk API')
    sys.path.insert(0, str(root / 'src'))
    import emberbsd_sdk
    require(type(emberbsd_sdk.API_VERSION) is int and emberbsd_sdk.API_VERSION == 1 and
            Path(emberbsd_sdk.__file__).resolve().parent == package,
            'the selected SDK must provide API version 1')
    from emberbsd_sdk.elf import read_elf_header
    from emberbsd_sdk.errors import CommandError, SDKError
    from emberbsd_sdk.inventory import sha256_file
    from emberbsd_sdk.jsonio import write_json
    from emberbsd_sdk.paths import canonical_existing, canonical_new
    from emberbsd_sdk.process import capture
    return SimpleNamespace(root=str(root), CommandError=CommandError, SDKError=SDKError,
                           sha256_file=sha256_file, write_json=write_json,
                           canonical_existing=canonical_existing, canonical_new=canonical_new,
                           read_elf_header=read_elf_header, capture=capture)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', choices=TARGETS, default='aarch64')
    parser.add_argument('--sdk-source', default=os.environ.get('EMBERBSD_SDK_SOURCE'))
    parser.add_argument('--helper', default=str(Path(__file__).resolve().parent.parent /
                        'recipes/graphics/gdk-pixbuf2/files/target-tools.py'))
    parser.add_argument('cross_tools', metavar='CROSS_TOOLS')
    parser.add_argument('new_work', metavar='NEW_WORK')
    options = parser.parse_args()
    require(sys.implementation.name == 'cpython' and sys.version_info[:2] == (3, 15),
            'select build-host CPython 3.15')
    require(os.path.isabs(sys.executable), 'sys.executable must be absolute')
    sdk = load_sdk(options.sdk_source)
    python = sdk.canonical_existing(sys.executable)
    require(os.access(python, os.X_OK), 'selected Python is not executable')
    triplet, machine = TARGETS[options.target]
    tools = Path(sdk.canonical_existing(options.cross_tools))
    cc = sdk.canonical_existing(str(tools / 'bin' / (triplet + '-gcc')))
    readelf = sdk.canonical_existing(str(tools / 'bin' / (triplet + '-readelf')))
    helper = sdk.canonical_existing(options.helper)
    require(os.path.isabs(options.new_work), 'new absolute work required')
    work = Path(sdk.canonical_new(options.new_work))
    require(not os.path.lexists(work), 'new absolute work required')
    for directory in ('build/provider', 'sysroot', 'cache', 'bin'):
        (work / directory).mkdir(parents=True)
    environment = dict(os.environ, EMBERBSD_SDK_SOURCE=sdk.root,
                       EMBERBSD_GI_QUERY_CONFIG=str(work / 'config.json'),
                       PATH=str(work / 'bin') + ':/usr/bin:/bin',
                       PYTHONDONTWRITEBYTECODE='1', FIXTURE_ROOT=str(work))
    for name in ('LD_LIBRARY_PATH', 'LD_PRELOAD', 'DYLD_LIBRARY_PATH', 'EMBERBSD_GI_TARGET'):
        environment.pop(name, None)

    def completed(command, *, env=environment):
        try:
            return sdk.capture(list(map(os.fspath, command)), cwd=str(work), env=env)
        except sdk.CommandError as error:
            return subprocess.CompletedProcess(error.argv, error.returncode, error.stdout, error.stderr)

    def compile_fixture(name, *command):
        result = completed(command)
        (work / (name + '.log')).write_bytes(result.stdout + result.stderr)
        require(result.returncode == 0,
                f'{name} failed ({result.returncode}): {(result.stdout + result.stderr).decode("utf-8", "replace")}')
        return (result.stdout + result.stderr).decode('utf-8', 'replace')

    # Exercise the production entry point in an isolated stdlib-only child.
    # No SDK source or query config is supplied. Runtime refusal must precede
    # SDK/config access and leave the helper cache and transport untouched.
    runtime_guards = []
    guard_environment = dict(environment)
    for name in ('EMBERBSD_SDK_SOURCE', 'EMBERBSD_GI_QUERY_CONFIG', 'EMBERBSD_GI_TARGET'):
        guard_environment.pop(name, None)
    for guard in ('version', 'implementation'):
        result = completed([python, '-I', '-c', RUNTIME_GUARD, helper, guard], env=guard_environment)
        (work / ('runtime-' + guard + '.stdout')).write_bytes(result.stdout)
        (work / ('runtime-' + guard + '.stderr')).write_bytes(result.stderr)
        require(result.returncode == 1 and not result.stdout and
                b'use the selected build-host CPython 3.15' in result.stderr,
                f'{guard}: unsupported runtime did not fail before SDK/config access')
        require(not (work / 'config.json').exists() and not list((work / 'cache').iterdir()),
                f'{guard}: runtime refusal created query configuration or work')
        runtime_guards.append({'name': guard, 'exit_status': result.returncode,
                               'sdk_imported': False, 'query_work_created': False})

    version = compile_fixture('native-python-version', python, '--version')
    sdk.write_json(str(work / 'native-python-provider.json'), {
        'path': python, 'sha256': sdk.sha256_file(python), 'version': version.strip(),
        'sdk_source': sdk.root, 'sdk_api': 1,
    })
    version = compile_fixture('cross-compiler-version', cc, '-dumpfullversion')
    require(re.fullmatch(r'16(?:\.[0-9]+)*\s*', version) is not None,
            'target fixtures require the common GCC16 cross compiler')
    build = work / 'build'
    query = build / 'gdk-pixbuf-query-loaders'
    printer = build / 'gdk-pixbuf-print-mime-types'
    module = build / 'libpixbufloader-probe.so'
    provider = build / 'provider/libpixbuf-probe.so.1'
    (build / 'library.c').write_text('int pixbuf_probe_answer(void) { return 42; }\n', encoding='utf-8')
    (build / 'query.c').write_text(
        'extern int pixbuf_probe_answer(void); void _start(void) { (void)pixbuf_probe_answer(); }\n',
        encoding='utf-8')
    (build / 'module.c').write_text(
        'extern int pixbuf_probe_answer(void); int pixbuf_probe_module(void) { return pixbuf_probe_answer(); }\n',
        encoding='utf-8')
    compile_fixture('provider', cc, '-nostdlib', '-shared', '-fPIC', build / 'library.c',
                    '-Wl,-soname,libpixbuf-probe.so.1', '-o', provider)
    compile_fixture('query', cc, '-nostdlib', '-Wl,-e,_start', build / 'query.c',
                    '-L' + str(provider.parent), '-Wl,-l:libpixbuf-probe.so.1', '-o', query)
    compile_fixture('module', cc, '-nostdlib', '-shared', '-fPIC', build / 'module.c',
                    '-Wl,-soname,libpixbufloader-probe.so', '-L' + str(provider.parent),
                    '-Wl,-l:libpixbuf-probe.so.1', '-o', module)
    shutil.copyfile(query, printer)
    original_provider = provider.read_bytes()
    cache = build / 'loaders.cache'
    cache.write_text(f'"{module}"\n', encoding='utf-8')
    config = {'build_root': str(build), 'sysroot': str(work / 'sysroot'),
              'cache': str(work / 'cache'), 'readelf': readelf, 'ssh': 'unused.invalid',
              'library_dirs': [str(provider.parent)]}
    if options.target != 'aarch64':
        config['target'] = options.target
    sdk.write_json(str(work / 'config.json'), config)
    sdk.write_json(str(work / 'input-provenance.json'), {
        'target': options.target, 'sdk_source': sdk.root, 'sdk_api': 1,
        'python': {'path': python, 'sha256': sdk.sha256_file(python)},
        'compiler': {'path': cc, 'sha256': sdk.sha256_file(cc), 'version': version.strip()},
        'readelf': {'path': readelf, 'sha256': sdk.sha256_file(readelf)},
        'helper': {'path': helper, 'sha256': sdk.sha256_file(helper)},
        'contract': {'path': str(Path(__file__).resolve()), 'sha256': sdk.sha256_file(str(Path(__file__).resolve()))},
        'elf': {path.name: sdk.sha256_file(str(path)) for path in (query, printer, module, provider)},
        'boundary': 'Real GCC16 target ELF fixtures; controlled host SSH executable; no target execution',
    })
    ssh = work / 'bin/ssh'
    ssh.write_text('#!' + python + '\n' + FAKE_SSH, encoding='utf-8')
    ssh.chmod(0o755)
    results = []

    def run(name, arguments, *, expected=None, error=None, phases=None):
        provider.write_bytes(original_provider)
        result = completed([python, '-E', '-S', helper, *arguments], env=dict(environment, FIXTURE_MODE=name))
        (work / (name + '.stdout')).write_bytes(result.stdout)
        (work / (name + '.stderr')).write_bytes(result.stderr)
        if error is None:
            require(result.returncode == 0, f'{name}: {result.stderr.decode("utf-8", "replace")}')
            if expected is not None:
                require(result.stdout == expected, f'{name}: wrong output')
        else:
            require(result.returncode != 0 and error.encode('utf-8') in result.stderr,
                    f'{name}: wrong failure boundary ({result.returncode}): {result.stderr.decode("utf-8", "replace")}')
            require(not result.stdout, f'{name}: failure published stdout')
        trace = work / (name + '.phases')
        if phases is not None:
            require(trace.read_text(encoding='utf-8').split() == phases.split(), f'{name}: wrong transport phases')
        else:
            require(not trace.exists(), f'{name}: refused input reached SSH')
        results.append({'name': name, 'exit_status': result.returncode, 'expected_error': error,
                        'phases': phases.split() if phases is not None else []})

    run('check', ['--check', build, work / 'sysroot', readelf])
    readelf_directory = work / 'readelf-directory'
    readelf_directory.mkdir(mode=0o755)
    readelf_directory.chmod(0o755)
    require(os.access(readelf_directory, os.X_OK), 'readelf directory fixture is not executable')
    sdk.write_json(str(work / 'config.json'), dict(config, readelf=str(readelf_directory)), exclusive=False)
    run('directory-readelf', ['--check', build, work / 'sysroot', readelf_directory],
        error='expected a regular file')
    sdk.write_json(str(work / 'config.json'), dict(config, host_key_alias='unsafe alias'), exclusive=False)
    run('invalid-host-alias', ['--check', build, work / 'sysroot', readelf], error='invalid host key alias')
    config['host_key_alias'] = 'target.example'
    sdk.write_json(str(work / 'config.json'), config, exclusive=False)
    run('loader-success', ['--loaders', query, module], expected=f'"{module}"\n'.encode('utf-8'),
        phases='allocate transfer query cleanup')
    require('HostKeyAlias=target.example' in
            (work / 'loader-success.ssh-argv').read_text(encoding='utf-8').splitlines(),
            'selected host key alias did not reach SSH')
    invalid_cache = build / 'invalid-utf8.cache'
    invalid_cache.write_bytes(cache.read_bytes() + b'# invalid UTF-8: \xff\n')
    run('mime-cache-invalid-utf8', ['--mime', printer, invalid_cache], error='utf-8')
    run('loader-invalid-utf8', ['--loaders', query, module], error='utf-8',
        phases='allocate transfer query cleanup')
    run('mime-success', ['--mime', printer, cache], expected=b'image/png;',
        phases='allocate transfer cache query cleanup')
    mime_cache = (work / 'mime-success.cache').read_bytes()
    require(b'/tmp/ember-pixbuf.AbCd1234/loaders/libpixbufloader-probe.so' in mime_cache and
            str(module).encode('utf-8') not in mime_cache, 'MIME cache did not map the verified module')
    for mode, error in (('loader-invalid', 'query output contains remote path'),
                        ('remote-path', 'query output contains remote path'),
                        ('cleanup', 'remote cleanup failed'), ('query', 'target query failed'),
                        ('source-change', 'source providers changed')):
        run(mode, ['--loaders', query, module], error=error, phases='allocate transfer query cleanup')
    run('transfer', ['--loaders', query, module], error='transfer failed', phases='allocate transfer cleanup')
    run('mime-invalid', ['--mime', printer, cache], error='invalid MIME query output',
        phases='allocate transfer cache query cleanup')
    run('duplicate-module', ['--loaders', query, module, module], error='duplicate target modules')
    run('missing-module', ['--loaders', query], error='missing target modules')
    run('wrong-tool', ['--loaders', printer, module], error='unexpected target tool')
    foreign = build / 'libpixbufloader-native.so'
    host_true = shutil.which('true', path='/usr/bin:/bin')
    require(host_true is not None, 'the host requires its base-system true executable')
    shutil.copyfile(host_true, foreign)
    # A host can share the target ELF class and machine. In that case, keep the
    # same negative boundary by changing e_machine in a real GCC16 ELF fixture.
    try:
        shares_target_header = sdk.read_elf_header(str(foreign), machine=machine) is not None
    except sdk.SDKError:
        shares_target_header = False
    native_fixture = 'native host executable'
    if shares_target_header:
        changed = bytearray(module.read_bytes())
        changed[18:20] = struct.pack('<H', 183 if machine == 62 else 62)
        foreign.write_bytes(changed)
        native_fixture = 'real GCC16 ELF with a foreign e_machine'
    processor = 'x86_64' if options.target == 'amd64' else 'aarch64'
    run('native-module', ['--loaders', query, foreign], error=f'not little-endian {processor} ELF64')
    script = (work / 'loader-success.query').read_text(encoding='utf-8')
    require(script.count('done < files.sha256') == 2 and 'timeout -k 5 60' in script,
            'production query lost its hash checks or deadline')
    require('StrictHostKeyChecking=yes' in Path(helper).read_text(encoding='utf-8'),
            'production helper lost strict SSH host-key checking')
    sdk.write_json(str(work / 'results.json'), {
        'passed': [result['name'] for result in results], 'count': len(results), 'results': results,
        'target': options.target, 'target_execution': False, 'native_fixture': native_fixture,
        'runtime_guards': runtime_guards,
        'cleanup': 'Only owned staging and archive duplicates are removed. Source fixtures and receipts remain.',
    })
    # Retain all source fixtures and receipts. Remove only this run's duplicates.
    for query_work in (work / 'cache').iterdir():
        require(query_work.is_dir() and not query_work.is_symlink() and
                query_work.name.startswith('pixbuf-tool-'), 'unexpected helper work entry')
        stage, archive = query_work / 'stage', query_work / 'input.tar.gz'
        if stage.exists():
            require(stage.is_dir() and not stage.is_symlink(), 'unexpected stage entry')
            shutil.rmtree(stage)
        if archive.exists():
            require(archive.is_file() and not archive.is_symlink(), 'unexpected archive entry')
            archive.unlink()
    print(f'PASS: {len(results)} pixbuf contract cases; real GCC16 ELF, no target execution; evidence {work}')
    return 0


RUNTIME_GUARD = r'''from pathlib import Path
import runpy
import sys
from types import SimpleNamespace

helper = Path(sys.argv[1]).resolve(strict=True)
kind = sys.argv[2]
sys.path.insert(0, str(helper.parent))
module = runpy.run_path(str(helper), run_name='pixbuf_runtime_guard_fixture')
if kind == 'version':
    sys.version_info = (3, 14, 0, 'final', 0)
elif kind == 'implementation':
    values = vars(sys.implementation).copy()
    values['name'] = 'unsupported-python'
    sys.implementation = SimpleNamespace(**values)
else:
    raise RuntimeError('unknown runtime fixture')
status = module['main'](['--check', 'unused-work', 'unused-sysroot', 'unused-readelf'])
if any(name == 'emberbsd_sdk' or name.startswith('emberbsd_sdk.') for name in sys.modules):
    print('unsupported runtime imported SDK before refusal', file=sys.stderr)
    raise SystemExit(96)
raise SystemExit(status)
'''


FAKE_SSH = r'''import os
from pathlib import Path
import sys

command = sys.argv[-1]
mode = os.environ['FIXTURE_MODE']
phase = ('allocate' if 'mktemp' in command else 'transfer' if command.startswith('tar ') else
         'cache' if command.startswith('cat > ') else 'query' if command == 'sh -s' else
         'cleanup' if command.startswith('rm -rf ') else 'unknown')
if phase == 'unknown':
    raise SystemExit('unexpected test transport command')
root = Path(os.environ['FIXTURE_ROOT'])
with (root / (mode + '.phases')).open('a', encoding='utf-8') as output:
    output.write(phase + '\n')
if phase in ('transfer', 'query', 'cache'):
    data = sys.stdin.buffer.read()
    if phase in ('query', 'cache'):
        (root / (mode + '.' + phase)).write_bytes(data)
if mode == phase:
    raise SystemExit(74)
if phase == 'allocate':
    (root / (mode + '.ssh-argv')).write_text('\n'.join(sys.argv[1:]) + '\n', encoding='utf-8')
    print('/tmp/ember-pixbuf.AbCd1234')
if phase == 'query':
    if mode == 'source-change':
        (root / 'build/provider/libpixbuf-probe.so.1').write_bytes(b'changed')
    if mode == 'mime-success':
        sys.stdout.write('image/png;')
    elif mode == 'mime-invalid':
        print('image/png;')
    elif mode == 'loader-invalid-utf8':
        sys.stdout.buffer.write(b'"/tmp/ember-pixbuf.AbCd1234/loaders/libpixbufloader-probe.so"\n# \xff\n')
    elif mode == 'loader-invalid':
        print('"/tmp/ember-pixbuf.AbCd1234/loaders/other.so"')
    elif mode == 'remote-path':
        print('# /tmp/ember-pixbuf.AbCd1234')
    else:
        print('"/tmp/ember-pixbuf.AbCd1234/loaders/libpixbufloader-probe.so"')
'''


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        sdk_errors = sys.modules.get('emberbsd_sdk.errors')
        if not isinstance(error, (OSError, RuntimeError, ValueError, ImportError)) and not (
                sdk_errors is not None and isinstance(error, sdk_errors.SDKError)):
            raise
        print(f'error: {error}', file=sys.stderr)
        raise SystemExit(1)
