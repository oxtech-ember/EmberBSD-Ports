#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Real ELF fixtures; rejected inputs never reach SSH.
"""Check GI target queries with GCC16 ELF fixtures and a refusing transport."""

import argparse
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import struct
import subprocess
import sys
import tarfile
from types import SimpleNamespace

sys.dont_write_bytecode = True

TARGETS = {
    'aarch64': ('aarch64', 'aarch64--netbsd', 183),
    'amd64': ('x86_64', 'x86_64--netbsd', 62),
}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def load_sdk(source):
    require(source is not None, 'set --sdk-source or EMBERBSD_SDK_SOURCE')
    require(os.path.isabs(source), 'SDK source must be absolute')
    root = Path(source).resolve(strict=True)
    module_root = root / 'src'
    require((module_root / 'emberbsd_sdk' / '__init__.py').is_file(),
            'SDK source does not contain src/emberbsd_sdk')
    sys.path.insert(0, str(module_root))
    import emberbsd_sdk
    require(emberbsd_sdk.API_VERSION == 1, 'unsupported EmberBSD SDK API')
    require(Path(emberbsd_sdk.__file__).resolve().parent ==
            (module_root / 'emberbsd_sdk').resolve(strict=True),
            'SDK import differs from the selected source')
    from emberbsd_sdk.errors import CommandError, SDKError
    from emberbsd_sdk.inventory import sha256_file
    from emberbsd_sdk.jsonio import write_json
    from emberbsd_sdk.paths import canonical_existing, canonical_new
    from emberbsd_sdk.process import capture
    return SimpleNamespace(root=str(root), CommandError=CommandError,
                           SDKError=SDKError, sha256_file=sha256_file,
                           write_json=write_json,
                           canonical_existing=canonical_existing,
                           canonical_new=canonical_new, capture=capture)


def arguments():
    recipe = (Path(__file__).resolve().parent.parent / 'recipes' / 'devel' /
              'gobject-introspection')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', choices=TARGETS, default='aarch64')
    parser.add_argument('--sdk-source', default=os.environ.get('EMBERBSD_SDK_SOURCE'))
    parser.add_argument('--helper', default=str(recipe / 'files' / 'target-query.py'))
    parser.add_argument('--cross-mk', default=str(recipe / 'cross.mk'))
    parser.add_argument('--elf-needed', default=str(recipe / 'files' / 'elf-needed.sh'))
    parser.add_argument('cross_tools', metavar='CROSS_TOOLS')
    parser.add_argument('new_work', metavar='NEW_WORK')
    return parser.parse_args()


def main():
    options = arguments()
    require(sys.version_info[:2] == (3, 15),
            'GI contracts require the selected build-host CPython 3.15')
    require(os.path.isabs(sys.executable) and Path(sys.executable).is_file() and
            os.access(sys.executable, os.X_OK),
            'sys.executable must name an absolute executable')
    sdk = load_sdk(options.sdk_source)
    python = sdk.canonical_existing(sys.executable)
    target = options.target
    processor, triplet, machine = TARGETS[target]
    tools = Path(sdk.canonical_existing(options.cross_tools))
    cc = sdk.canonical_existing(str(tools / 'bin' / (triplet + '-gcc')))
    readelf = sdk.canonical_existing(str(tools / 'bin' / (triplet + '-readelf')))
    helper = sdk.canonical_existing(options.helper)
    cross_mk = sdk.canonical_existing(options.cross_mk)
    needed = sdk.canonical_existing(options.elf_needed)
    require(os.path.isabs(options.new_work), 'new absolute work required')
    work = Path(sdk.canonical_new(options.new_work))
    require(not os.path.lexists(work), 'new absolute work required')
    work.mkdir(parents=True)
    work = Path(sdk.canonical_existing(str(work)))
    for directory in ('build', 'build/provider', 'sysroot', 'cache', 'bin', 'outside'):
        (work / directory).mkdir(parents=True, exist_ok=True)

    def capture(*command, env=None, input=None):
        environment = os.environ.copy()
        if env is not None:
            for key, value in env.items():
                if value is None:
                    environment.pop(key, None)
                else:
                    environment[key] = value
        try:
            return sdk.capture(list(map(os.fspath, command)), cwd=str(work),
                               env=environment, input=input)
        except sdk.CommandError as exc:
            return subprocess.CompletedProcess(exc.argv, exc.returncode,
                                               exc.stdout, exc.stderr)

    def combined(result):
        return (result.stdout + result.stderr).decode('utf-8', 'replace')

    def record(name, result):
        output = combined(result)
        (work / (name + '.log')).write_text(output, encoding='utf-8')
        return output

    def run(name, *command, env=None, input=None):
        result = capture(*command, env=env, input=input)
        output = record(name, result)
        require(result.returncode == 0, f'{name}: {output}')
        return output

    def write_config(value):
        sdk.write_json(str(config_path), value, exclusive=not config_path.exists())

    run('native-python-version', python, '--version')
    sdk.write_json(str(work / 'native-python-provider.json'), {
        'path': python, 'sha256': sdk.sha256_file(python),
        'version': sys.version, 'sdk_source': sdk.root, 'sdk_api': 1,
    })
    version = run('compiler-version', cc, '-dumpfullversion')
    require(re.fullmatch(r'16(?:\.[0-9]+)*\s*', version) is not None,
            'target fixtures require the common GCC16 cross compiler')
    (work / 'build/library.c').write_text(
        'int gi_probe_answer(void) { return 42; }\n', encoding='utf-8')
    (work / 'build/query.c').write_text(
        'extern int gi_probe_answer(void); void _start(void) { (void)gi_probe_answer(); }\n',
        encoding='utf-8')
    run('dso', cc, '-nostdlib', '-shared', '-fPIC', work / 'build/library.c',
        '-Wl,-soname,libgi-probe.so.1', '-o', work / 'build/provider/libgi-probe.so.1')
    run('elf', cc, '-nostdlib', '-Wl,-e,_start', work / 'build/query.c',
        '-L' + str(work / 'build/provider'), '-Wl,-l:libgi-probe.so.1',
        '-o', work / 'build/query')
    (work / 'provider-alias').symlink_to(work / 'build/provider')
    marker = work / 'ssh-reached'
    ssh_arguments = work / 'ssh-arguments'
    ssh_fixture = work / 'bin/ssh'
    ssh_fixture.write_text(
        '#!/bin/sh\nprintf \'%s\\n\' "$@" > ' + shlex.quote(str(ssh_arguments)) +
        '\nprintf \'%s\\n\' reached >> ' + shlex.quote(str(marker)) + '\nexit 74\n',
        encoding='utf-8')
    ssh_fixture.chmod(0o755)
    config = {
        'build_root': str(work / 'build'), 'sysroot': str(work / 'sysroot'),
        'cache': str(work / 'cache'), 'readelf': readelf, 'ssh': 'unused.invalid',
        'library_dirs': [str(work / 'provider-alias')],
    }
    if target != 'aarch64':
        config['target'] = target
    config_path = work / 'config.json'
    write_config(config)
    environment = {
        'EMBERBSD_GI_QUERY_CONFIG': str(config_path), 'EMBERBSD_SDK_SOURCE': sdk.root,
        'PATH': str(work / 'bin') + ':/usr/bin:/bin',
        'EMBERBSD_GI_TARGET': None,
        'LD_LIBRARY_PATH': None, 'DYLD_LIBRARY_PATH': None, 'LD_PRELOAD': None,
    }

    def reject(name, pattern, *args, env=None, failure=None):
        selected_env = dict(environment)
        if env is not None:
            selected_env.update(env)
        result = capture(python, '-E', '-S', helper, *args, env=selected_env)
        output = record(name, result)
        require(result.returncode != 0 and re.search(pattern, output) is not None
                and not marker.exists(),
                f'{name} did not fail at expected boundary: {output}')
        if failure is not None:
            require(failure.is_file(), f'{name} left no failure marker')

    def reject_command(name, pattern, *args):
        failure = work / 'build' / (name + '-failure')
        reject(name, pattern, *args,
               env={'EMBERBSD_GI_FAILURE_MARKER': str(failure)}, failure=failure)

    run('check', python, '-E', '-S', helper, '--check', work / 'build', work / 'sysroot',
        readelf, target, env=environment)
    for number, value in enumerate((None, True, 1, [], {}, '', 'other',
                                    '../query', '/bin/query', 'bin/query')):
        write_config(dict(config, executable_layout=value))
        reject('invalid-layout-check-' + str(number), 'unsupported executable layout',
               '--check', work / 'build', work / 'sysroot', readelf, target)
        reject('invalid-layout-execute-' + str(number), 'unsupported executable layout',
               '--execute', work / 'build/query')
    for layout in ('flat', 'prefix-bin'):
        write_config(dict(config, executable_layout=layout))
        run('layout-check-' + layout, python, '-E', '-S', helper, '--check',
            work / 'build', work / 'sysroot', readelf, target, env=environment)
    write_config(config)
    # X_OK on a directory must not authenticate an executable readelf file.
    readelf_directory = work / 'readelf-directory'
    readelf_directory.mkdir(mode=0o755)
    readelf_directory.chmod(0o755)
    require(os.access(readelf_directory, os.X_OK), 'readelf directory fixture is not executable')
    write_config(dict(config, readelf=str(readelf_directory)))
    reject('directory-readelf', 'expected a regular file|readelf is not executable', '--check',
           work / 'build', work / 'sysroot', readelf_directory, target)
    write_config(config)
    # Real bmake evaluates the shared GI fragment for both target metadata sets.
    # This fixture selects variables. It does not accept a provider or VM.
    make_tree = work / 'make'
    (make_tree / 'devel/gobject-introspection').mkdir(parents=True)
    (make_tree / 'mk').mkdir()
    (make_tree / 'mk/bsd.prefs.mk').write_text('', encoding='utf-8')
    shutil.copyfile(cross_mk, make_tree / 'devel/gobject-introspection/cross.mk')
    (make_tree / 'devel/gobject-introspection/Makefile').write_text(
        '.include "cross.mk"\n', encoding='utf-8')
    make_base = [
        os.environ.get('BMAKE', 'bmake'), '-C', str(make_tree / 'devel/gobject-introspection'),
        'USE_CROSS_COMPILE=yes', 'OPSYS=NetBSD', 'CROSS_OPSYS=NetBSD',
        'CROSS_OS_VERSION=11.0', 'EMBERBSD_CROSS_BUILD_PYTHON=' + python,
        'EMBERBSD_SDK_SOURCE=' + sdk.root,
        'EMBERBSD_GI_QUERY_CONFIG=' + str(config_path),
        'EMBERBSD_GI_FILESDIR=' + str(Path(helper).parent),
        'EMBERBSD_CROSS_BUILD_CC=/usr/bin/cc', 'TOOLDIR=' + str(tools),
    ]
    for selected, (arch, gnu, _) in reversed(tuple(TARGETS.items())):
        args = ['MACHINE_ARCH=' + arch, 'CROSS_MACHINE_ARCH=' + arch,
                'MACHINE_GNU_PLATFORM=' + gnu, 'EMBERBSD_CROSS_TARGET=' + selected]
        reason = run('make-' + selected, *make_base, *args, '-V', '${PKG_FAIL_REASON}')
        require(not reason.strip(), 'supported GI target rejected: ' + reason)
        settings = run('make-env-' + selected, *make_base, *args, '-V', '${MAKE_ENV}')
        require('/bin/' + gnu + '-readelf' in settings and
                'EMBERBSD_GI_TARGET=' + selected in settings,
                'GI selected a foreign target readelf/environment')
        launchers = [item.partition('=')[2] for item in shlex.split(settings)
                     if item.startswith('GI_CROSS_LAUNCHER=')]
        require(len(launchers) == 1, 'missing or duplicate GI recipe launcher')
        launcher = shlex.split(launchers[0])
        require(launcher[:3] == [python, '-E', '-S'] and len(launcher) == 4,
                'GI recipe must isolate its selected host Python')
        if selected == target:
            # An explicit draft helper may have another basename.
            production_command = launcher[:3] + [helper]
        require(python in settings and
                'EMBERBSD_SDK_SOURCE=' + sdk.root in settings,
                'GI did not select the common Python and explicit SDK source')
        same = run('make-same-python-' + selected, *make_base, *args,
                   'EMBERBSD_GI_PYTHON=' + python, '-V', '${PKG_FAIL_REASON}')
        require(not same.strip(), 'matching GI/common Python selectors were rejected')
        alias_base = [argument for argument in make_base
                      if not argument.startswith('EMBERBSD_CROSS_BUILD_PYTHON=')]
        selected_python = run('make-alias-python-' + selected, *alias_base, *args,
                              'EMBERBSD_GI_PYTHON=' + python, '-V', '${EMBERBSD_CROSS_BUILD_PYTHON}',
                              env={'EMBERBSD_CROSS_BUILD_PYTHON': None, 'EMBERBSD_GI_PYTHON': None})
        require(selected_python.strip() == python, 'published GI Python alias did not select the common provider')
        rejected = run('make-mixed-python-' + selected, *make_base, *args,
                       'EMBERBSD_GI_PYTHON=/usr/bin/false', '-V', '${PKG_FAIL_REASON}')
        require('same Python provider' in rejected, 'mixed GI/common Python selectors were accepted')
        foreign = 'x86_64' if arch == 'aarch64' else 'aarch64'
        rejected = run('make-mixed-' + selected, *make_base, *args,
                       'CROSS_MACHINE_ARCH=' + foreign, '-V', '${PKG_FAIL_REASON}')
        require(bool(rejected.strip()), 'GI accepted mixed architecture metadata')
        rejected = run('make-mixed-gnu-' + selected, *make_base, *args,
                       'MACHINE_GNU_PLATFORM=foreign--netbsd', '-V', '${PKG_FAIL_REASON}')
        require(bool(rejected.strip()), 'GI accepted a foreign GNU provider')

    # pkgsrc's target sysconfig site must not select the host process backend.
    # Use the actual recipe argv. Keep the target library environment intact.
    pysite = work / 'pysite'
    pysite.mkdir()
    site_marker = work / 'sitecustomize-reached'
    (pysite / 'sitecustomize.py').write_text(
        'import sys\nsys.platform = "netbsd11"\n' +
        'with open(' + repr(str(site_marker)) + ', "w") as output:\n' +
        '    output.write("loaded\\n")\n', encoding='utf-8')
    isolated_environment = dict(environment, PYTHONPATH=str(pysite),
                                LD_LIBRARY_PATH=str(work / 'provider-alias'))
    if sys.platform in ('darwin', 'linux'):
        result = capture(production_command[0], production_command[-1],
                         work / 'build/query', env=isolated_environment)
        output = record('host-site-unisolated', result)
        require(result.returncode != 0 and 'NetBSD process ' in output and
                site_marker.is_file() and not marker.exists(),
                'unisolated target site did not reproduce the host backend failure: ' + output)
        site_marker.unlink()
    result = capture(*production_command, '--check', work / 'build',
                     work / 'sysroot', readelf, target, env=isolated_environment)
    output = record('host-site-isolated-check', result)
    require(result.returncode == 0 and not site_marker.exists() and not marker.exists(),
            'recipe host preflight loaded target sitecustomize: ' + output)
    library_marker = work / 'ssh-library-path'
    ordinary_ssh = ssh_fixture.read_text(encoding='utf-8')
    ssh_fixture.write_text(
        '#!/bin/sh\nprintf "%s\\n" "$LD_LIBRARY_PATH" > ' +
        shlex.quote(str(library_marker)) + '\n' + ordinary_ssh.split('\n', 1)[1],
        encoding='utf-8')
    result = capture(*production_command, work / 'build/query', env=isolated_environment)
    output = record('host-site-isolated-probe', result)
    require(result.returncode != 0 and 'allocate failed (74)' in output and
            marker.read_text(encoding='utf-8') == 'reached\n' and not site_marker.exists() and
            library_marker.read_text(encoding='utf-8').strip() == str(work / 'provider-alias'),
            'recipe host isolation lost the target environment or transport: ' + output)
    marker.unlink()
    ssh_fixture.write_text(ordinary_ssh, encoding='utf-8')

    write_config(dict(config, host_key_alias='unsafe alias'))
    reject('invalid-host-alias', 'invalid host key alias', '--check',
           work / 'build', work / 'sysroot', readelf)
    config['host_key_alias'] = 'target.example'
    write_config(config)
    reject('different-sysroot', 'configuration differs', '--check',
           work / 'build', work / 'outside', readelf)
    reject('outside-binary', 'outside build root', '/usr/bin/true')
    shutil.copyfile('/usr/bin/true', work / 'build/native')
    reject('native-binary', 'not little-endian .* ELF64', work / 'build/native')
    other_target = 'amd64' if target == 'aarch64' else 'aarch64'
    write_config(dict(config, target=other_target))
    reject('foreign-query-config', 'configuration differs|not little-endian .* ELF64',
           '--check', work / 'build', work / 'sysroot', readelf, target)
    reject('foreign-query-architecture', 'not little-endian .* ELF64', work / 'build/query')
    legacy = dict(config)
    legacy.pop('target', None)
    write_config(legacy)
    if target == 'amd64':
        reject('legacy-is-not-amd64', 'configuration differs', '--check',
               work / 'build', work / 'sysroot', readelf, target)
    run('legacy-aarch64-check', python, '-E', '-S', helper, '--check', work / 'build',
        work / 'sysroot', readelf, env=environment)
    write_config(dict(config, target='unsupported'))
    reject('unknown-target', 'unsupported GI target', '--check', work / 'build',
           work / 'sysroot', readelf)
    write_config(config)
    provider = work / 'build/provider/libgi-probe.so.1'
    original = provider.read_bytes()
    foreign = bytearray(original)
    foreign[18:20] = struct.pack('<H', 183 if machine == 62 else 62)
    provider.write_bytes(foreign)
    reject('foreign-provider', 'not little-endian .* ELF64', work / 'build/query')
    foreign = bytearray(original)
    foreign[4] = 1
    provider.write_bytes(foreign)
    reject('foreign-class', 'not little-endian .* ELF64', work / 'build/query')
    foreign = bytearray(original)
    foreign[5] = 2
    provider.write_bytes(foreign)
    reject('foreign-endian', 'not little-endian .* ELF64', work / 'build/query')
    provider.write_bytes(original)
    reject('unsupported-args', 'only an optional', work / 'build/query', '--delete')
    (work / 'build/types').write_text('get-type:gi_probe_answer\n', encoding='utf-8')
    (work / 'outside/untouched').write_text('unchanged', encoding='utf-8')
    (work / 'build/output').symlink_to(work / 'outside/untouched')
    reject('output-symlink', 'output already exists', work / 'build/query',
           '--introspect-dump=' + str(work / 'build/types') + ',' + str(work / 'build/output'))
    require((work / 'outside/untouched').read_text(encoding='utf-8') == 'unchanged',
            'symlink target modified')
    write_config(dict(config, library_dirs=[]))
    reject('missing-provider', 'missing provider: libgi-probe.so.1', work / 'build/query')
    write_config(dict(config, sysroot=str(work / 'build')))
    reject('overlapping-roots', r'build/sysroot overlap', '--check', work / 'build',
           work / 'build', readelf)
    write_config(config)
    # Explicit SDK libraries need no artificial NEEDED entry in the program.
    sdk_lib = work / 'sysroot/usr/pkg/lib'
    sdk_lib.mkdir(parents=True)
    input_provider = sdk_lib / 'libgi-input.so.2'
    input_alias = sdk_lib / 'libgi-input.so'
    (work / 'build/input.c').write_text(
        'extern int gi_probe_answer(void); int gi_input_answer(void) { return gi_probe_answer(); }\n')
    run('input-dso', cc, '-nostdlib', '-shared', '-fPIC', work / 'build/input.c',
        '-Wl,-soname,libgi-input.so.2', '-L' + str(provider.parent),
        '-Wl,-l:libgi-probe.so.1', '-o', input_provider)
    input_original = input_provider.read_bytes()
    input_alias.symlink_to(input_provider.name)
    library_input = {'name': input_alias.name, 'sha256': sdk.sha256_file(str(input_provider))}

    def reject_library(name, pattern, entries):
        write_config(dict(config, library_inputs=entries))
        reject('library-' + name, pattern, '--execute', work / 'build/query')

    for number, value in enumerate((None, 'libgi-input.so', {})):
        reject_library('list-' + str(number), 'bounded array', value)
    reject_library('count', 'bounded array', [library_input] * 33)
    for number, value in enumerate((None, {}, dict(library_input, source=str(input_provider)))):
        reject_library('entry-' + str(number), 'invalid library input entry', [value])
    for name in ('', '.', '..', '../libgi-input.so', '/libgi-input.so', 'lib/file', '-library'):
        reject_library('name-' + str(len(name)) + name.replace('/', '_'), 'unsafe or duplicate',
                       [dict(library_input, name=name)])
    reject_library('duplicate', 'unsafe or duplicate', [library_input, library_input])
    for number, value in enumerate((None, 'F' * 64, '0' * 63)):
        reject_library('sha-format-' + str(number), 'invalid library input SHA256',
                       [dict(library_input, sha256=value)])
    reject_library('missing', 'missing or ambiguous', [dict(library_input, name='libmissing.so')])
    reject_library('hash', 'input SHA256 differs', [dict(library_input, sha256='0' * 64)])
    input_alias.unlink(); shutil.copyfile(input_provider, input_alias)
    reject_library('regular', 'must be a symbolic link', [library_input])
    input_alias.unlink()
    for number, target_link in enumerate(('/tmp/libgi-input.so.2', '../libgi-input.so.2',
                                          input_alias.name)):
        input_alias.symlink_to(target_link)
        reject_library('target-' + str(number), 'direct basename link|expected a regular file', [library_input])
        input_alias.unlink()
    chain = sdk_lib / 'libgi-chain.so'
    chain.symlink_to(input_provider.name); input_alias.symlink_to(chain.name)
    reject_library('chain', 'expected a regular file', [library_input])
    input_alias.unlink(); chain.unlink(); input_alias.symlink_to(input_provider.name)
    second_lib = work / 'sysroot/usr/lib'
    second_lib.mkdir(parents=True)
    shutil.copyfile(input_provider, second_lib / input_provider.name)
    (second_lib / input_alias.name).symlink_to(input_provider.name)
    reject_library('ambiguous', 'missing or ambiguous', [library_input])
    (second_lib / input_alias.name).unlink()
    for label, offset, value in (('machine', 18, 183 if machine == 62 else 62), ('type', 16, 2)):
        changed = bytearray(input_original); changed[offset:offset+2] = struct.pack('<H', value)
        input_provider.write_bytes(changed)
        reject_library(label, 'expected ELF64|requires ET_DYN',
                       [dict(library_input, sha256=sdk.sha256_file(str(input_provider)))])
    input_provider.write_bytes(input_original)
    no_soname = sdk_lib / 'libgi-no-soname.so'
    run('input-no-soname', cc, '-nostdlib', '-shared', '-fPIC', work / 'build/library.c', '-o', no_soname)
    input_alias.unlink(); input_alias.symlink_to(no_soname.name)
    reject_library('no-soname', 'requires ET_DYN and a safe SONAME',
                   [dict(library_input, sha256=sdk.sha256_file(str(no_soname)))])
    input_alias.unlink(); input_alias.symlink_to(input_provider.name)
    copy = sdk_lib / 'libgi-copy.so.2'; shutil.copyfile(input_provider, copy)
    copy_alias = sdk_lib / 'libgi-copy.so'; copy_alias.symlink_to(copy.name)
    reject_library('soname-conflict', 'conflicting SDK library input SONAME',
                   [library_input, dict(library_input, name=copy_alias.name)])
    copy_alias.unlink()
    collision = sdk_lib / 'libgi-probe.so.1'; collision.symlink_to(input_provider.name)
    reject_library('alias-collision', 'alias collides with a provider',
                   [dict(library_input, name=collision.name)])
    collision.unlink()
    (provider.parent / 'libgi-build-only.so').symlink_to(provider.name)
    reject_library('build-only', 'missing or ambiguous', [dict(library_input, name='libgi-build-only.so')])
    # Equal bytes do not permit a different provider for an explicit SDK SONAME.
    candidate = work / 'build/input-candidate/libgi-input.so.2'
    candidate.parent.mkdir()
    shutil.copyfile(input_provider, candidate)
    require(candidate.resolve() != input_provider.resolve() and
            sdk.sha256_file(str(candidate)) == library_input['sha256'],
            'provider identity control needs distinct paths with equal bytes')
    (work / 'build/input-query.c').write_text(
        'extern int gi_input_answer(void); void _start(void) { (void)gi_input_answer(); }\n')
    input_query = work / 'build/input-query'
    run('input-needed-elf', cc, '-nostdlib', '-Wl,-e,_start', work / 'build/input-query.c',
        '-L' + str(candidate.parent), '-Wl,-l:libgi-input.so.2',
        '-L' + str(provider.parent), '-Wl,-l:libgi-probe.so.1', '-o', input_query)
    from emberbsd_sdk.elf import read_elf_dynamic
    require(input_provider.name in read_elf_dynamic(str(input_query), machine=machine)['needed'],
            'provider identity control needs the declared SONAME in NEEDED')
    write_config(dict(config, library_inputs=[library_input],
                      library_dirs=[str(candidate.parent), str(provider.parent)]))
    reject('library-needed-same-bytes-different-provider', 'declared SDK provider differs',
           '--execute', input_query)
    write_config(dict(config, library_inputs=[]))
    run('empty-library-inputs', python, '-E', '-S', helper, '--check', work / 'build',
        work / 'sysroot', readelf, target, env=environment)
    write_config(config)
    print('PASS: explicit SDK library list/name/hash, direct-link, source, ELF, SONAME '
          'and collision refusals before SSH; empty list retains the ordinary contract')
    # Execute data never shares the query/lib/types/manifest namespace. Use the
    # same real ELF fixtures, but refuse malformed data before the first SSH.
    resource = work / 'sysroot/STEP'
    resource.write_bytes(b'upstream resource fixture\n')
    resource_hash = sdk.sha256_file(str(resource))
    artifact = {'source': str(resource), 'path': 'data/occt/XSTEPResource/STEP',
                'sha256': resource_hash}
    data_config = dict(config, execute_inputs=[artifact], execute_environment={
        'CSF_LANGUAGE': {'literal': 'us'},
        'CSF_STEPDefaults': {'stage_path': 'data/occt/XSTEPResource'},
    })

    def reject_data(name, pattern, *, entries=None, values=None, execute=True):
        selected = dict(data_config)
        if entries is not None:
            selected['execute_inputs'] = entries
        if values is not None:
            selected['execute_environment'] = values
        write_config(selected)
        args = ['--execute'] if execute else []
        reject('data-' + name, pattern, *args, work / 'build/query')

    reject_data('gi-mode', 'data inputs require --execute', execute=False)
    for name, path in (('query', 'query'), ('library', 'lib/file'),
                       ('types', 'types.txt'), ('manifest', 'files.sha256'),
                       ('absolute', '/data/file'), ('traversal', 'data/../file'),
                       ('empty-component', 'data//file')):
        reject_data(name, 'unsafe data destination', entries=[dict(artifact, path=path)])
    reject_data('duplicate', 'colliding data destination', entries=[artifact, artifact])
    reject_data('prefix', 'colliding data destination', entries=[
        dict(artifact, path='data/occt'), artifact])
    outside_data = work / 'outside/resource'
    outside_data.write_bytes(resource.read_bytes())
    reject_data('outside', 'data source outside target/build roots',
                entries=[dict(artifact, source=str(outside_data))])
    resource_alias = work / 'sysroot/STEP-alias'
    resource_alias.symlink_to(resource)
    reject_data('symlink', 'canonical real ancestors',
                entries=[dict(artifact, source=str(resource_alias))])
    reject_data('directory', 'expected a regular file',
                entries=[dict(artifact, source=str(resource.parent))])
    reject_data('hash', 'data input SHA256 differs',
                entries=[dict(artifact, sha256='0' * 64)])
    reject_data('hash-format', 'invalid data SHA256',
                entries=[dict(artifact, sha256='F' * 64)])
    large_data = work / 'sysroot/large-data'
    with large_data.open('wb') as output:
        output.truncate(16 * 1024 * 1024 + 1)
    reject_data('large', 'data file exceeds 16 MiB',
                entries=[dict(artifact, source=str(large_data))])
    reject_data('count', 'bounded array', entries=[artifact] * 1025)
    for name in ('PATH', 'LD_PRELOAD', 'LD_LIBRARY_PATH', 'CSF_' + 'x' * 61):
        reject_data('env-' + name, 'bounded CSF resource environment names',
                    values={name: {'stage_path': 'data/occt'}})
    reject_data('undeclared-path', 'path has no declared data',
                values={'CSF_STEPDefaults': {'stage_path': 'data/undeclared'}})
    reject_data('literal-path', 'path has no declared data',
                values={'CSF_STEPDefaults': {'literal': '/usr/share/occt'}})
    reject_data('language', 'invalid CSF language literal',
                values={'CSF_LANGUAGE': {'literal': 'us; touch invalid'}})
    # Change an already opened source after its stable snapshot. The SDK's
    # regular-file primitive is the only injected boundary; ELF inspection and
    # the production bounded read remain real. Neither case reaches SSH.
    mutator = work / 'data-copy-mutation.py'
    mutator.write_text(DATA_COPY_MUTATION, encoding='utf-8')
    write_config(data_config)
    for mode in ('grow', 'shrink'):
        resource.write_bytes(b'upstream resource fixture\n')
        result = capture(python, '-E', '-S', mutator, helper, sdk.root,
                         resource, mode, work / 'build/query', env=environment)
        output = record('data-copy-' + mode, result)
        require(result.returncode != 0 and 'data source size changed while copying' in output
                and not marker.exists(), f'data {mode} did not refuse its bounded copy: {output}')
    resource.write_bytes(b'upstream resource fixture\n')
    write_config(config)
    print('PASS: execute data namespaces, source identities, hashes, size/count bounds, '
          'CSF-only environment and growing/shrinking input refusals before SSH')
    # The real cross-linked fixture resolves only through the directory alias.
    result = capture(python, '-E', '-S', helper, work / 'build/query', env=environment)
    output = record('valid-alias', result)
    require(result.returncode != 0 and 'allocate failed (74)' in output and
            marker.read_text(encoding='utf-8') == 'reached\n',
            'valid target/alias did not reach bounded transport')
    allocation = ssh_arguments.read_text(encoding='utf-8').splitlines()[-1]
    require('test "$(uname -s)" = NetBSD' in allocation and
            'test "$(uname -p)" = ' + processor in allocation,
            'selected target uname contract missing')
    # Literal execute arguments use the same verified transport.
    marker.unlink()
    result = capture(python, '-E', '-S', helper, '--execute', work / 'build/query',
                     'two words', "single'quote", '', env=environment)
    output = record('execute-args', result)
    require(result.returncode != 0 and 'allocate failed (74)' in output and
            marker.read_text(encoding='utf-8') == 'reached\n',
            'execute argv did not reach bounded transport')
    # Waf runs getconf LFS_CFLAGS. Only the sysroot regular file may run.
    marker.unlink()
    reject_command('missing-command', 'target command missing from sysroot: getconf',
                   '--execute', 'getconf', 'LFS_CFLAGS')
    (work / 'sysroot/usr/bin').mkdir(parents=True)
    (work / 'sysroot/bin').mkdir(parents=True)
    shutil.copyfile(work / 'build/query', work / 'sysroot/bin/sh')
    (work / 'sysroot/usr/bin/getconf').symlink_to('../../bin/sh')
    reject_command('symlinked-command', 'not a sysroot regular file: getconf',
                   '--execute', 'getconf', 'LFS_CFLAGS')
    (work / 'sysroot/usr/bin/getconf').unlink()
    shutil.copyfile(work / 'build/query', work / 'sysroot/usr/bin/getconf')
    reject('command-without-execute', 'unsupported target command: getconf', 'getconf')
    reject_command('unlisted-command', 'unsupported target command: sh',
                   '--execute', 'sh', '-c', 'true')
    before = set((work / 'cache').glob('gi-query-*'))
    result = capture(python, '-E', '-S', helper, '--execute', 'getconf', 'LFS_CFLAGS', env=environment)
    output = record('execute-getconf', result)
    require(result.returncode != 0 and 'allocate failed (74)' in output and
            marker.read_text(encoding='utf-8') == 'reached\n',
            'sysroot getconf did not reach bounded transport')
    created = set((work / 'cache').glob('gi-query-*')) - before
    require(len(created) == 1, 'missing getconf receipt')
    getconf = work / 'sysroot/usr/bin/getconf'
    receipt = sdk.sha256_file(str(getconf)) + '  ' + str(getconf)
    require(receipt in (created.pop() / 'sources.sha256').read_text(encoding='utf-8').splitlines(),
            'getconf receipt names another program')
    print('PASS: execute mode runs only the sysroot getconf for target commands')

    # Execute the production identity body with explicit host fixtures.
    # No VM, SSH target or target executable runs in this regression.
    identity_allocated = work / 'identity-allocated'
    identity_glue = (
        'uname() { case "$1" in -s) printf \'%s\\n\' "$GI_FIXTURE_OPSYS";; '
        '-p) printf \'%s\\n\' "$GI_FIXTURE_PROCESSOR";; *) return 2;; esac; }\n'
        'mktemp() { printf \'allocated\\n\' > ' + shlex.quote(str(identity_allocated)) +
        '; printf \'/tmp/ember-gir.AbCd1234\\n\'; }\n'
    )
    for opsys, arch, accepted in (
            ('NetBSD', processor, True),
            ('NetBSD', 'x86_64' if processor == 'aarch64' else 'aarch64', False),
            ('Linux', processor, False)):
        identity_allocated.unlink(missing_ok=True)
        result = capture('sh', '-s', env={'GI_FIXTURE_OPSYS': opsys,
                         'GI_FIXTURE_PROCESSOR': arch},
                         input=(identity_glue + allocation).encode('utf-8'))
        require((result.returncode == 0) == accepted and
                identity_allocated.exists() == accepted,
                'remote identity did not gate allocation')
    print('PASS: both target make metadata sets, explicit/default JSON targets, '
          'foreign ELF/class/endian and real identity shell guard')
    needed_env = {'EMBERBSD_GI_READELF': readelf, 'EMBERBSD_GI_TARGET': target}
    output = run('needed', 'sh', needed, work / 'build/query', env=needed_env)
    require(output == 'libgi-probe.so.1\n', 'wrong target SONAME')
    result = capture('sh', needed, work / 'build/native', env=needed_env)
    require(result.returncode != 0, 'native image accepted by SONAME helper')
    result = capture('sh', needed, work / 'build/query',
                     env=dict(needed_env, EMBERBSD_GI_TARGET=other_target))
    require(result.returncode != 0, 'foreign machine accepted by SONAME helper')
    for invalid in ('', 'unsupported'):
        result = capture('sh', needed, work / 'build/query',
                         env=dict(needed_env, EMBERBSD_GI_TARGET=invalid))
        require(result.returncode != 0 and 'unsupported GI target' in combined(result),
                'empty or unknown SONAME target did not fail closed')

    # Inject only transport outcomes. Board acceptance runs upstream binaries.
    ssh_fixture.write_text('#!' + python + '\n' + FAKE_SSH, encoding='utf-8')
    (work / 'build/output').unlink()
    # These fixtures select a real installed sysroot ELF provider. The earlier
    # alias fixture keeps checking an in-tree provider that must be uploaded.
    (work / 'sysroot/usr/pkg/lib').mkdir(parents=True, exist_ok=True)
    installed = work / 'sysroot/usr/pkg/lib/libgi-probe.so.1'
    shutil.copyfile(provider, installed)
    write_config(dict(config, library_dirs=[str(installed.parent)]))
    expected = {
        'reuse': ('allocate reuse cleanup', 'reuse failed'),
        'reuse-unknown': ('allocate reuse cleanup', 'invalid reused library response'),
        'reuse-duplicate': ('allocate reuse cleanup', 'invalid reused library response'),
        'reused': ('allocate reuse transfer query readback cleanup', None),
        'transfer': ('allocate reuse transfer cleanup', 'transfer failed'),
        'query': ('allocate reuse transfer query cleanup', 'target query failed'),
        'readback': ('allocate reuse transfer query readback cleanup', 'invalid introspection XML'),
        'bad-xml': ('allocate reuse transfer query readback cleanup', 'invalid introspection XML'),
        'oversized-xml': ('allocate reuse transfer query readback cleanup', 'invalid introspection XML'),
        'xml-stderr-overflow': ('allocate reuse transfer query readback cleanup', 'invalid introspection XML'),
        'cleanup': ('allocate reuse transfer query readback cleanup', 'remote cleanup failed'),
        'input-change': ('allocate reuse transfer query readback cleanup', 'source providers changed'),
        'success': ('allocate reuse transfer query readback cleanup', None),
    }
    for mode, (phases, error) in expected.items():
        (work / 'build/types').write_text('original type query\n', encoding='utf-8')
        trace = work / (mode + '-phases.txt')
        outcome = work / 'build' / (mode + '.xml')
        transport_env = dict(environment, GI_TEST_MODE=mode,
                             GI_TEST_PHASES=str(trace), GI_TEST_INPUT=str(work / 'build/types'))
        before = set((work / 'cache').glob('gi-query-*'))
        result = capture(python, '-E', '-S', helper, work / 'build/query',
                         f'--introspect-dump={work}/build/types,{outcome}', env=transport_env)
        output = record('transport-' + mode, result)
        require(trace.read_text(encoding='utf-8').split() == phases.split(),
                f'{mode}: wrong transport phases')
        if error is not None:
            require(result.returncode != 0 and re.search(error, output) is not None,
                    f'{mode}: wrong failure boundary: {output}')
            require(not outcome.exists(), f'{mode}: published failed output')
            if mode == 'oversized-xml':
                created = set((work / 'cache').glob('gi-query-*')) - before
                require(len(created) == 1, 'oversized XML lost its query receipt')
                query_work = created.pop()
                transfer_log = (query_work / 'xml-transfer.log').read_text(encoding='utf-8')
                require('refused:' in transfer_log and 'stdout_limit=16777216' in transfer_log,
                        'oversized XML lost its bounded transfer refusal log')
                require(not (query_work / 'dump.xml').exists(),
                        'oversized XML published a local dump')
            if mode == 'xml-stderr-overflow':
                created = set((work / 'cache').glob('gi-query-*')) - before
                require(len(created) == 1, 'XML stderr overflow lost its query receipt')
                transfer_log = (created.pop() / 'xml-transfer.log').read_bytes()
                require(transfer_log.startswith(b'exit=0 bytes=14\n') and
                        len(transfer_log) <= 1024 * 1024 + 128,
                        'XML stderr overflow lost its bounded transport receipt')
        else:
            require(result.returncode == 0 and
                    outcome.read_text(encoding='utf-8') == '<dump></dump>\n',
                    f'{mode}: valid output missing: {output}')

    # Execute the production reuse shell body. Map only target paths and sha256.
    reuse_body = next((work / 'cache').glob('*/reuse.sh')).read_text(encoding='utf-8')
    reuse_root = work / 'reuse-shell'
    body = reuse_body.replace('/tmp/ember-gir.AbCd1234', str(reuse_root)).replace(
        '/usr/pkg/lib/libgi-probe.so.1', str(installed))
    sha_glue = ('sha256() { test "$1" = -q || return 2; shift; '
                '/usr/bin/shasum -a 256 "$1" | cut -d \' \' -f 1; }\n')
    for mode in ('matched', 'changed', 'missing', 'corrupted-copy'):
        if reuse_root.exists():
            shutil.rmtree(reuse_root)
        reuse_root.mkdir()
        shutil.copyfile(provider, installed)
        if mode == 'changed':
            installed.write_text('different installed file', encoding='utf-8')
        if mode == 'missing':
            installed.unlink()
        corruption = ('cp() { /bin/cp "$1" "$2" && printf corrupted >> "$2"; }\n'
                      if mode == 'corrupted-copy' else '')
        result = capture('sh', '-s', input=(sha_glue + corruption + body).encode('utf-8'))
        output = record('reuse-shell-' + mode, result)
        copied = reuse_root / 'lib/libgi-probe.so.1'
        if mode == 'matched':
            require(result.returncode == 0 and output == 'libgi-probe.so.1\n' and
                    sdk.sha256_file(str(copied)) == sdk.sha256_file(str(installed)),
                    'reuse did not copy matching provider')
        elif mode in ('changed', 'missing'):
            require(result.returncode == 0 and not output and not copied.exists(),
                    'reuse did not fall back to transfer')
        else:
            require(result.returncode == 92 and not output,
                    'reuse accepted corrupt copied bytes')
    print('PASS: production reuse shell copies identical bytes, falls back for '
          'missing/changed files and rejects copy corruption')
    print('PASS: real ELF and alias resolution; refusals before SSH; SONAME checks; '
          'transport failures, installed-provider reuse and successful publication')
    # Both fixed executable layouts preserve the original streams and status.
    for label, layout in (('omitted', None), ('flat', 'flat'), ('prefix-bin', 'prefix-bin'),
                          ('input-flat', 'flat'), ('input-prefix', 'prefix-bin')):
        selected = dict(config, library_dirs=[str(installed.parent)])
        if label.startswith('input-'):
            selected['library_inputs'] = [library_input]
        if layout is not None:
            selected['executable_layout'] = layout
        write_config(selected)
        relative = 'bin/query' if layout == 'prefix-bin' else 'query'
        for mode in ('execute-pass', 'execute-fail', 'execute-literal'):
            name = label + '-' + mode
            phase_file = work / (name + '-phases')
            archive_file = work / (name + '-input.tar.gz')
            execute_args = (['two words', "single'quote", '', '--sdk-source', '/literal/source']
                            if mode == 'execute-literal' else [])
            selected_env = dict(environment, GI_TEST_MODE=mode, GI_TEST_PHASES=str(phase_file),
                                GI_TEST_EXECUTABLE=relative, GI_TEST_ARCHIVE=str(archive_file),
                                GI_TEST_ARGV=json.dumps(execute_args),
                                GI_TEST_ARGV_RECEIPT=str(work / (name + '-argv.json')))
            before = set((work / 'cache').glob('gi-query-*'))
            result = capture(python, '-E', '-S', helper, '--execute', work / 'build/query',
                             *execute_args, env=selected_env)
            record(name, result)
            expected_status = 7 if mode == 'execute-fail' else 0
            require(result.stdout == b'probe stdout\n' and result.stderr == b'probe stderr\n'
                    and result.returncode == expected_status,
                    f'{name}: lost probe streams/status')
            require(phase_file.read_text(encoding='utf-8').splitlines() ==
                    ['allocate', 'reuse', 'transfer', 'query', 'status', 'cleanup'],
                    f'{name}: missing cleanup')
            from emberbsd_sdk.jsonio import read_json
            require(read_json(str(work / (name + '-argv.json'))) == execute_args,
                    f'{name}: changed literal execute arguments')
            with tarfile.open(archive_file, 'r:gz') as archive:
                expected = './' + relative
                other = './query' if relative != 'query' else './bin/query'
                require(expected in archive.getnames() and other not in archive.getnames(),
                        f'{name}: wrong executable archive path')
                member = archive.getmember(expected)
                require(member.isfile() and member.mode & 0o777 == 0o755 and
                        archive.extractfile(member).read() == (work / 'build/query').read_bytes(),
                        f'{name}: executable bytes/mode changed')
                manifest = archive.extractfile('./files.sha256').read().decode('ascii').splitlines()
                require(sdk.sha256_file(str(work / 'build/query')) + '  ' + relative in manifest and
                        sdk.sha256_file(str(installed)) + '  lib/libgi-probe.so.1' in manifest,
                        f'{name}: manifest lost executable/provider identity')
                if label.startswith('input-'):
                    require(library_input['sha256'] + '  lib/libgi-input.so.2' in manifest and
                            library_input['sha256'] + '  lib/libgi-input.so' in manifest and
                            './lib/libgi-input.so' not in archive.getnames() and
                            archive.extractfile('./lib/libgi-input.so.2').read() == input_original,
                            f'{name}: explicit DSO/alias identity or usual closure missing')
            created = set((work / 'cache').glob('gi-query-*')) - before
            require(len(created) == 1, f'{name}: missing query receipt')
            receipt = created.pop()
            require((receipt / 'cleanup.log').read_bytes().startswith(b'0\n') and
                    not (receipt / 'stage').exists() and not (receipt / 'input.tar.gz').exists(),
                    f'{name}: temporary stage survived cleanup')
            if label.startswith('input-'):
                evidence = read_json(str(receipt / 'library-inputs.json'))['inputs']
                require(len(evidence) == 1 and evidence[0]['name'] == library_input['name'] and
                        evidence[0]['sha256'] == library_input['sha256'] and
                        evidence[0]['soname'] == input_provider.name and
                        evidence[0]['provider'] == str(input_provider), 'SDK input provenance differs')
    write_config(dict(config, library_dirs=[str(installed.parent)]))
    print('PASS: omitted/flat/prefix-bin layouts preserve ELF bytes, mode, manifests, '
          'literal arguments, separate streams, status0/7 and cleanup')
    write_config(dict(config, library_dirs=[str(installed.parent)],
                      executable_layout='prefix-bin', library_inputs=[library_input]))
    phases = work / 'library-before-transfer-phases'
    failure = work / 'build/library-before-transfer-failure'
    result = capture(python, '-E', '-S', helper, '--execute', work / 'build/query', env=dict(
        environment, GI_TEST_MODE='library-before-transfer', GI_TEST_PHASES=str(phases),
        GI_TEST_LIBRARY_ALIAS=str(input_alias), EMBERBSD_GI_FAILURE_MARKER=str(failure)))
    output = record('library-before-transfer', result)
    require(result.returncode != 0 and 'SDK library input identity changed' in output
            and failure.is_file() and phases.read_text().splitlines() == ['allocate', 'reuse', 'cleanup'],
            'changed SDK alias was transferred or accepted without infrastructure refusal')
    write_config(dict(config, library_dirs=[str(installed.parent)]))
    print('PASS: source SDK alias change after allocation/reuse refuses before transfer and cleans')
    for mode in ('query', 'status', 'cleanup'):
        failure = work / 'build' / (mode + '-failure')
        result = capture(python, '-E', '-S', helper, '--execute', work / 'build/query', env=dict(
            environment, GI_TEST_MODE=mode,
            GI_TEST_PHASES=str(work / ('execute-' + mode + '-phases')),
            EMBERBSD_GI_FAILURE_MARKER=str(failure)))
        require(result.returncode != 0 and failure.is_file(),
                f'Unrecorded execute infrastructure failure: {mode}: {combined(result)}')
    failure = work / 'build/execute-stderr-overflow-failure'
    phases = work / 'execute-stderr-overflow-phases'
    result = capture(python, '-E', '-S', helper, '--execute', work / 'build/query', env=dict(
        environment, GI_TEST_MODE='execute-stderr-overflow', GI_TEST_PHASES=str(phases),
        EMBERBSD_GI_FAILURE_MARKER=str(failure)))
    record('execute-stderr-overflow', result)
    require(result.returncode != 0 and failure.is_file() and not result.stdout and
            b'capture limit' in result.stderr,
            'truncated failed probe became a legitimate negative configure result')
    require(phases.read_text(encoding='utf-8').split() ==
            ['allocate', 'reuse', 'transfer', 'query', 'cleanup'],
            'truncated failed probe did not clean its remote work')
    print('PASS: query/status/cleanup failures cannot become silent negative configure results')
    # Run the actual production manifest loops and CSF exports in a host shell.
    # Only timeout is adapted: it checks staged data instead of running a target
    # ELF. This is transport acceptance, not a target OCCT or loader test.
    write_config(dict(data_config, library_dirs=[str(installed.parent)]))
    data_mock = work / 'data-remote'
    for mode, error in (('data-pass', None), ('data-child', None),
                        ('data-corrupt', 'execution-status failed'),
                        ('data-source', 'source providers changed'),
                        ('data-metadata', 'file changed during inspection'),
                        ('data-root', 'data root identity changed'),
                        ('data-prefix', None), ('data-library-flat', None),
                        ('data-library-prefix', None),
                        ('data-library-corrupt', 'execution-status failed'),
                        ('data-library-source', 'SDK library input identity changed')):
        relative = 'bin/query' if mode in ('data-prefix', 'data-library-prefix') else 'query'
        write_config(dict(data_config, library_dirs=[str(installed.parent)],
                          library_inputs=[library_input] if mode.startswith('data-library-') else [],
                          executable_layout='prefix-bin' if relative == 'bin/query' else 'flat'))
        resource.write_bytes(b'upstream resource fixture\n')
        resource.chmod(0o644)
        trace = work / (mode + '-phases')
        failure = work / 'build' / (mode + '-failure')
        saved_tar = work / (mode + '-input.tar.gz')
        saved_script = work / (mode + '-query.sh')
        selected_env = dict(environment, GI_TEST_MODE=mode, GI_TEST_PHASES=str(trace),
                            GI_TEST_DATA_MOCK=str(data_mock),
                            GI_TEST_DATA_SOURCE=str(resource),
                            GI_TEST_DATA_BUILD=str(work / 'build'),
                            GI_TEST_DATA_TAR=str(saved_tar), GI_TEST_DATA_SCRIPT=str(saved_script),
                            GI_TEST_DATA_SHA=resource_hash, GI_TEST_EXECUTABLE=relative,
                            GI_TEST_LIBRARY_ALIAS=str(input_alias),
                            GI_TEST_LIBRARY_SHA=library_input['sha256'],
                            EMBERBSD_GI_FAILURE_MARKER=str(failure))
        before = set((work / 'cache').glob('gi-query-*'))
        result = capture(python, '-E', '-S', helper, '--execute', work / 'build/query',
                         env=selected_env)
        output = record(mode, result)
        if mode == 'data-root':
            replacement = work / 'build'
            replacement.rename(work / 'build-replacement-observed')
            (work / 'build-original').rename(replacement)
            # The failure marker belongs to the replacement root that the
            # helper actually observed, not the restored fixture root.
            failure = work / 'build-replacement-observed' / failure.name
        require(trace.read_text(encoding='utf-8').splitlines() ==
                ['allocate', 'reuse', 'transfer', 'query', 'status', 'cleanup'],
                f'{mode}: data transport skipped cleanup')
        require(not data_mock.exists(), f'{mode}: data remote was not removed')
        if error is None:
            require(result.returncode == 0 and result.stdout == b'probe stdout\n'
                    and result.stderr == b'probe stderr\n' and not failure.exists(),
                    f'{mode}: real manifest/export shell failed: {output}')
        else:
            require(result.returncode != 0 and error in output and failure.is_file(),
                    f'{mode}: wrong resource refusal boundary: {output}')
        created = set((work / 'cache').glob('gi-query-*')) - before
        require(len(created) == 1, f'{mode}: missing data provenance receipt')
        from emberbsd_sdk.jsonio import read_json
        receipt = read_json(str(created.pop() / 'data-inputs.json'))
        require(receipt['files'][0]['sha256'] == resource_hash and
                receipt['files'][0]['path'] == artifact['path'] and
                receipt['environment'] == data_config['execute_environment'],
                f'{mode}: data identity/environment receipt changed')
        require(saved_tar.is_file() and saved_script.is_file(),
                f'{mode}: missing exact transport inputs')
    write_config(config)
    print('PASS: production execute shell verifies real data hashes and CSF paths; '
          'unrelated root children pass; data corruption, source metadata/bytes '
          'and root replacement fail with remote cleanup')
    return 0


DATA_COPY_MUTATION = r'''import importlib.util
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
helper, sdk, source, mode, executable = sys.argv[1:]
sys.path.insert(0, str(Path(helper).parent))
sys.path.insert(0, str(Path(sdk) / 'src'))
import emberbsd_sdk.paths as paths
from emberbsd_sdk import inventory  # Keep real stable hashes outside this injection.
original_open = paths.open_regular
def mutate(path):
    handle, info = original_open(path)
    if os.fspath(path) == source:
        with open(source, 'ab' if mode == 'grow' else 'wb') as output:
            if mode == 'grow':
                output.write(b'x')
    return handle, info
paths.open_regular = mutate
spec = importlib.util.spec_from_file_location('selected_target_query', helper)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
raise SystemExit(module.main(['--sdk-source', sdk, '--execute', executable]))
'''


FAKE_SSH = r'''import json
import os
import shlex
import shutil
import subprocess
import tarfile
import io
from pathlib import Path
import sys

command = sys.argv[-1]
mode = os.environ['GI_TEST_MODE']
if 'mktemp' in command:
    phase = 'allocate'
elif command.startswith('tar '):
    phase = 'transfer'
elif command == 'sh -s -- ember-gir-reuse':
    phase = 'reuse'
elif command == 'sh -s':
    phase = 'query'
elif command.startswith('cat ') and 'execution.status' in command:
    phase = 'status'
elif command.startswith('test -s '):
    phase = 'readback'
elif command.startswith('rm -rf '):
    phase = 'cleanup'
else:
    raise SystemExit('unexpected test transport command')
with open(os.environ['GI_TEST_PHASES'], 'a', encoding='utf-8') as trace:
    trace.write(phase + '\n')
script = b''
if phase in ('transfer', 'query', 'reuse'):
    script = sys.stdin.buffer.read()
if mode == phase:
    raise SystemExit(74)
if phase == 'transfer' and 'GI_TEST_ARCHIVE' in os.environ:
    Path(os.environ['GI_TEST_ARCHIVE']).write_bytes(script)
if phase == 'reuse' and mode == 'library-before-transfer':
    alias = Path(os.environ['GI_TEST_LIBRARY_ALIAS'])
    target = os.readlink(alias); alias.unlink(); alias.symlink_to(target)
if mode.startswith('data-'):
    mock = Path(os.environ['GI_TEST_DATA_MOCK'])
    if phase == 'allocate':
        mock.mkdir(mode=0o700)
        print('/tmp/ember-gir.AbCd1234')
    elif phase == 'transfer':
        Path(os.environ['GI_TEST_DATA_TAR']).write_bytes(script)
        with tarfile.open(fileobj=io.BytesIO(script), mode='r:gz') as archive:
            archive.extractall(mock, filter='data')
    elif phase == 'query':
        Path(os.environ['GI_TEST_DATA_SCRIPT']).write_bytes(script)
        body = script.decode('utf-8').replace('/tmp/ember-gir.AbCd1234', str(mock))
        glue = ("sha256() { test \"$1\" = -q || return 2; shift; "
                "/usr/bin/shasum -a 256 \"$1\" | cut -d ' ' -f 1; }\n"
                "timeout() {\n"
                "  test \"$4\" = \"$GI_TEST_DATA_MOCK/$GI_TEST_EXECUTABLE\" && test -x \"$4\" || return 83\n"
                "  test \"$CSF_LANGUAGE\" = us || return 84\n"
                "  test \"$CSF_STEPDefaults\" = \"$GI_TEST_DATA_MOCK/data/occt/XSTEPResource\" || return 85\n"
                "  test \"$(sha256 -q \"$CSF_STEPDefaults/STEP\")\" = \"$GI_TEST_DATA_SHA\" || return 86\n"
                "  if test \"$GI_TEST_MODE\" = data-corrupt; then printf corrupted >> \"$CSF_STEPDefaults/STEP\"; fi\n"
                "  case \"$GI_TEST_MODE\" in data-library-*)\n"
                "    test \"$(readlink lib/libgi-input.so)\" = libgi-input.so.2 || return 87\n"
                "    test \"$(sha256 -q lib/libgi-input.so)\" = \"$GI_TEST_LIBRARY_SHA\" || return 88;; esac\n"
                "  if test \"$GI_TEST_MODE\" = data-library-corrupt; then rm lib/libgi-input.so; cp lib/libgi-input.so.2 lib/libgi-input.so; fi\n"
                "  printf 'probe stdout\\n'\n  printf 'probe stderr\\n' >&2\n}\n")
        result = subprocess.run(['sh', '-s'], input=(glue + body).encode('utf-8'),
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
        if mode == 'data-library-source':
            alias = Path(os.environ['GI_TEST_LIBRARY_ALIAS'])
            target = os.readlink(alias); alias.unlink(); alias.symlink_to(target)
        if mode == 'data-source':
            Path(os.environ['GI_TEST_DATA_SOURCE']).write_bytes(b'changed resource\n')
        if mode == 'data-metadata':
            Path(os.environ['GI_TEST_DATA_SOURCE']).chmod(0o600)
        if mode == 'data-child':
            (Path(os.environ['GI_TEST_DATA_BUILD']) / 'unrelated-child').write_bytes(b'allowed\n')
        if mode == 'data-root':
            build = Path(os.environ['GI_TEST_DATA_BUILD'])
            original = build.with_name('build-original')
            build.rename(original)
            shutil.copytree(original, build, symlinks=True, copy_function=shutil.copy2)
        sys.stdout.buffer.write(result.stdout)
        sys.stderr.buffer.write(result.stderr)
        raise SystemExit(result.returncode)
    elif phase == 'status':
        status = mock / 'execution.status'
        if not status.is_file():
            raise SystemExit(74)
        sys.stdout.buffer.write(status.read_bytes())
    elif phase == 'cleanup':
        shutil.rmtree(mock)
    raise SystemExit(0)
if phase == 'allocate':
    print('/tmp/ember-gir.AbCd1234')
elif phase == 'reuse':
    if mode == 'reuse-unknown':
        print('unexpected.so')
    if mode == 'reuse-duplicate':
        print('libgi-probe.so.1\nlibgi-probe.so.1')
    if mode == 'reused':
        print('libgi-probe.so.1')
elif phase == 'query':
    if mode.startswith('execute-'):
        if mode in ('execute-pass', 'execute-fail', 'execute-literal'):
            invocations = [line for line in script.decode('utf-8').splitlines()
                           if line.startswith('timeout ')]
            if len(invocations) != 1:
                raise SystemExit('production query has no unique invocation')
            invocation = shlex.split(invocations[0])
            expected = ['timeout', '-k', '5', '60',
                        '/tmp/ember-gir.AbCd1234/' + os.environ['GI_TEST_EXECUTABLE']]
            arguments = json.loads(os.environ['GI_TEST_ARGV'])
            if invocation != expected + arguments + ['>', 'stdout.log', '2>', 'stderr.log']:
                raise SystemExit('production query lost literal execute arguments')
            Path(os.environ['GI_TEST_ARGV_RECEIPT']).write_text(
                json.dumps(invocation[5:-4]) + '\n', encoding='utf-8')
        if mode == 'execute-stderr-overflow':
            sys.stdout.write('probe stdout\n')
            sys.stderr.buffer.write(b'e' * (1024 * 1024 + 1))
            raise SystemExit(7)
        sys.stdout.write('probe stdout\n')
        sys.stderr.write('probe stderr\n')
        raise SystemExit(7 if mode == 'execute-fail' else 0)
    if mode == 'input-change':
        Path(os.environ['GI_TEST_INPUT']).write_text('modified', encoding='utf-8')
elif phase == 'status':
    print('7' if mode == 'execute-fail' else '0')
elif phase == 'readback':
    if mode == 'xml-stderr-overflow':
        sys.stdout.write('<dump></dump>\n')
        sys.stderr.buffer.write(b'e' * (1024 * 1024 + 1))
    elif mode == 'oversized-xml':
        sys.stdout.buffer.write(b'<dump>' + b'x' * (16 * 1024 * 1024))
    else:
        print('not XML' if mode == 'bad-xml' else '<dump></dump>')
'''


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, ImportError) as exc:
        print(f'error: {exc}', file=sys.stderr)
        raise SystemExit(1)
