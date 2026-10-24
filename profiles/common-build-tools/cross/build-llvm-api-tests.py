#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Link real consumers against staged shared LLVM.
import os
from pathlib import Path
import re
import shlex
import shutil
import sys
import tarfile
sys.dont_write_bytecode = True
from llvm_host import checked_paths, load_sdk, log_run, query


def build(args):
    from emberbsd_sdk.inventory import sha256_file
    from emberbsd_sdk.jsonio import read_json, write_json
    from emberbsd_sdk.elf import read_elf_dynamic
    if len(args) != 4:
        raise ValueError('Use CROSS_TOOLS SYSROOT HOST_LLVM_CONFIG NEW_WORK')
    checked_paths(args)
    tools, sysroot, config = map(os.path.realpath, args[:3])
    work = args[3]
    if os.path.lexists(work):
        raise ValueError('NEW_WORK must be unused')
    owner = Path(__file__).resolve().parent
    prefix = query([config, '--prefix'])
    receipt_path = str(Path(config).parents[1] / 'receipt.json')
    metadata = read_json(receipt_path)
    if not os.path.isabs(prefix) or not os.path.isdir(prefix) or metadata['target_prefix'] != prefix or metadata['sysroot'] != sysroot or not metadata.get('staged_library_sha256'):
        raise ValueError('Require validated staged target prefix and matching sysroot')
    triple = query([config, '--host-target'])
    match = re.fullmatch(r'(aarch64|x86_64)-(?:unknown)?-netbsd(?:[0-9]+(?:\.[0-9]+)*)?', triple)
    if query([config, '--version']) != '23.1.4' or not match:
        raise ValueError('Require staged LLVM23.1.4 for supported NetBSD CPU')
    arch = match[1]
    machine = {'aarch64': 183, 'x86_64': 62}[arch]
    if query([config, '--has-rtti']) != 'YES' or query([config, '--link-shared', '--shared-mode', 'core', 'bitreader', 'bitwriter', 'orcjit', 'native']) != 'shared':
        raise ValueError('LLVM must have shared linkage and RTTI')
    cc, cxx, readelf = [tools + '/bin/' + arch + '--netbsd-' + name for name in ('gcc', 'g++', 'readelf')]
    if query([cc, '-dumpmachine']) != arch + '--netbsd' or query([cc, '-dumpfullversion']) != '16.2.0':
        raise ValueError('Common GCC16 target compiler required')
    libraries = shlex.split(query([config, '--link-shared', '--libfiles', 'core', 'bitreader', 'bitwriter', 'orcjit', 'native']))
    if len(libraries) != 1 or not libraries[0].startswith(prefix + '/lib/'):
        raise ValueError('Expected one staged shared LLVM provider')
    library = os.path.realpath(libraries[0])
    if sha256_file(library) != metadata['staged_library_sha256']:
        raise ValueError('Shared LLVM differs from metadata tool receipt')
    dynamic = read_elf_dynamic(library, machine=machine)
    soname = dynamic['soname']
    if not soname or not re.fullmatch(r'libLLVM(?:-23)?\.so(?:\.23(?:\.1(?:\.2)?)?)?', soname):
        raise ValueError('Unexpected shared LLVM SONAME')
    sources = ['llvm-c-api-test.c', 'llvm-orc-test.cpp', 'run-llvm-api-tests.sh']
    inputs = [str(owner / name) for name in sources] + [__file__, cc, cxx, readelf, config, library, receipt_path]
    initial = {p: sha256_file(os.path.realpath(p)) for p in inputs}
    Path(work, 'bundle/bin').mkdir(parents=True)
    Path(work, 'bundle/source').mkdir()
    Path(work, 'bundle/target-arch.txt').write_text(arch + '\n')
    for name in sources[:2]:
        shutil.copyfile(owner / name, Path(work, 'bundle/source', name))
    shutil.copyfile(owner / sources[2], Path(work, 'bundle', sources[2]))
    Path(work, 'bundle', sources[2]).chmod(0o755)
    link = shlex.split(query([config, '--ldflags'])) + shlex.split(query([config, '--link-shared', '--libs', '--system-libs', 'core', 'bitreader', 'bitwriter', 'orcjit', 'native']))
    link += ['-Wl,-rpath-link,' + p for p in (prefix + '/lib', sysroot + '/usr/pkg/lib', sysroot + '/usr/pkg/gcc16/lib')] + ['-Wl,-rpath,/usr/pkg/lib', '-Wl,-rpath,/usr/pkg/gcc16/lib']
    for name in ('llvm-c-api-test', 'llvm-orc-test'):
        is_c = name == 'llvm-c-api-test'
        flags = []
        for flag in shlex.split(query([config, '--cflags' if is_c else '--cxxflags'])):
            flags.extend(['-isystem', prefix + '/include'] if flag == '-I' + prefix + '/include' else [flag])
        if is_c:
            flags.append('-std=c11')
        source = work + '/bundle/source/' + name + ('.c' if is_c else '.cpp')
        binary = work + '/bundle/bin/' + name
        log_run(work + '/' + name + '.build.log', [cc if is_c else cxx, '--sysroot=' + sysroot, '-B' + sysroot + '/usr/pkg/gcc16/lib/gcc/' + arch + '--netbsd/16.2.0/', '-O2', '-Wall', '-Wextra', '-Werror', *flags, source, *link, '-o', binary])
        log_run(work + '/' + name + '.elf.log', [readelf, '-h', '-d', binary])
        result = read_elf_dynamic(binary, machine=machine)
        if soname not in result['needed'] or any(p in (result['rpath'] or '') + (result['runpath'] or '') for p in (prefix, sysroot, work)):
            raise ValueError('Invalid linked LLVM consumer metadata')
    Path(work, 'bundle/runtime-library.sha256').write_text(initial[library] + '  /usr/pkg/lib/' + soname + '\n')
    write_json(work + '/receipt.json', dict(compiler=cc, compiler_version=query([cc, '--version']), cxx=cxx, sysroot=sysroot, llvm_config=config, llvm_soname=soname, llvm_library_sha256=initial[library], sources=initial))
    if initial != {p: sha256_file(os.path.realpath(p)) for p in inputs}:
        raise ValueError('Input changed during build')
    Path(work, 'inputs.sha256').write_text(''.join(sha + '  ' + p + '\n' for p, sha in initial.items()))
    bundle = Path(work, 'bundle')
    Path(bundle, 'artifacts.sha256').write_text(''.join(sha256_file(p) + '  ' + str(p.relative_to(bundle)) + '\n' for p in sorted(bundle.rglob('*')) if p.is_file()))
    archive = work + '/llvm-api-tests.tar.gz'
    with tarfile.open(archive, 'w:gz') as output:
        output.add(bundle, arcname='.')
    print(sha256_file(archive) + '  ' + archive)


if __name__ == '__main__':
    from sdk_source import exit_error, install_signal_handlers
    install_signal_handlers()
    try:
        _, args = load_sdk()
        build(args)
    except Exception as error:
        exit_error(error)
