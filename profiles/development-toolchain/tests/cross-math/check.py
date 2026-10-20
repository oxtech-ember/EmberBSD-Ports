#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Run real target probes; never execute ELF.
import sys
sys.dont_write_bytecode = True
from pathlib import Path
import hashlib
import os
import re
import shutil

PROFILE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROFILE / 'runtime/recipe/files'))
import sdk_source
sys.path.insert(0, str(PROFILE))


def main(arguments):
    args = sdk_source.arguments(arguments)
    from emberbsd_sdk import jsonio
    from emberbsd_sdk.errors import CommandError
    from host import TARGETS, VERSION, build_path, new_path, require, capture, logged, prepare_source
    require(len(args) == 6, 'Usage: check.py TARGET EXPORTED_PKGSRC GCC_ARCHIVE GCC16_PREFIX SYSROOT NEW_WORK --sdk-source SOURCE')
    target, *values = args
    require(target in TARGETS, 'Unknown target')
    tree, archive, prefix, sysroot, work = [build_path(value) for value in values]
    new_path(work)
    triplet = TARGETS[target][0]
    here = Path(__file__).resolve().parent
    gcc, cxx = [prefix / 'bin' / (triplet + '-' + name) for name in ('gcc', 'g++')]
    make = os.environ.get('GNU_MAKE', '/usr/bin/make')
    env = {'PATH': str(prefix / 'bin') + ':' + os.environ.get('PATH', '')}
    require(capture([gcc, '-dumpfullversion'], env).strip() == VERSION and capture([gcc, '-dumpmachine'], env).strip() == triplet, 'GCC16 required')
    require(capture([make, '--version'], env).startswith('GNU Make '), 'GNU make required')
    names = re.findall(r'^auto address_(\w+) =', (here / 'imports.cc').read_text(), re.M)
    require(len(names) == 43 and len(set(names)) == 43, 'Expected 43 independent names')
    work.mkdir()
    results = []

    def run(label, command, expected=0, directory=None, extra=None):
        directory = directory or work
        extra = extra or {}
        command = [str(arg) for arg in command]
        log = work / (label + '.stdout')
        status = 0
        try:
            logged(command, log, dict(env, **extra), directory)
        except CommandError as error:
            status = error.returncode
        data = log.read_bytes()
        (work / (label + '.stderr')).write_bytes(b'')
        results.append({'name': label, 'argv': command, 'directory': str(directory), 'environment': extra, 'exit': status if status >= 0 else None, 'signal': -status if status < 0 else None, 'stdout_sha256': hashlib.sha256(data).hexdigest(), 'stderr_sha256': hashlib.sha256(b'').hexdigest(), 'output_streams': 'combined'})
        jsonio.write_json(work / 'results.json', results, exclusive=not (work / 'results.json').exists())
        require(status == expected, 'Unexpected result: ' + label + ': ' + str(status))
        return data.decode('utf-8')

    source = work / 'src'
    with (work / 'source.stdout').open('xb') as output:
        prepare_source(tree, archive, source, output=output)
    baseline = work / 'baseline'
    (baseline / 'libstdc++-v3').mkdir(parents=True)
    shutil.copy2(source / 'libstdc++-v3/configure', baseline / 'libstdc++-v3/configure')
    # Remove later configure deltas first; each reverse patch needs zero fuzz.
    for name in ('tls', 'math'):
        delta = tree / ('lang/gcc16/patches/patch-libstdc++-v3_configure_' + name)
        run('baseline-configure-' + name, ['patch', '-f', '-R', '-F', '0', '-p0', '-i', delta], directory=baseline)
    flags = ['--sysroot=' + str(sysroot), '-B' + str(sysroot / 'usr/pkg/gcc16/lib/gcc' / triplet / VERSION) + '/', '-B' + str(sysroot / 'usr/pkg/gcc16/lib') + '/']
    tools = {name.upper(): str(prefix / 'bin' / (triplet + '-' + name)) for name in 'ar as ld nm objcopy objdump ranlib readelf strip'.split()}
    build_triplet = capture(['sh', source / 'config.guess'], env).strip()
    gthreads = work / 'build' / triplet / 'libgcc'
    gthreads.mkdir(parents=True)
    rule = re.search(r'^gthr-default\.h: \$\(srcdir\)/\$\(thread_header\)\n\t-\$\(LN_S\) \$< \$@\n', (source / 'libgcc/Makefile.in').read_text(), re.M)
    require(rule, 'Upstream gthread rule changed')
    (work / 'gthreads.mk').write_text(rule[0])
    run('gthreads', [make, '-f', work / 'gthreads.mk', 'srcdir=' + str(source / 'libgcc'), 'thread_header=gthr-posix.h', 'LN_S=ln -s', 'gthr-default.h'], directory=gthreads)
    configure_args = ['--srcdir=' + str(source / 'libstdc++-v3'), '--build=' + build_triplet, '--host=' + triplet, '--target=' + triplet, '--with-cross-host=' + build_triplet, '--with-target-subdir=' + triplet, '--prefix=/usr/pkg/gcc16', '--libdir=/usr/pkg/gcc16/lib', '--with-toolexeclibdir=/usr/pkg/gcc16/lib', '--with-gxx-include-dir=/usr/pkg/gcc16/include/c++', '--with-sysroot=' + str(sysroot), '--with-gnu-as', '--with-gnu-ld', '--with-as=' + tools['AS'], '--with-ld=' + tools['LD'], '--disable-multilib', '--enable-shared', '--enable-threads=posix', '--enable-long-long', '--disable-libssp', '--disable-libstdcxx-pch', '--disable-nls', '--disable-year2038', '--cache-file=/dev/null']
    configure_env = dict(tools, CC=' '.join([str(gcc)] + flags), CXX=' '.join([str(gcc)] + flags + ['-shared-libgcc', '-nostdinc++']), CFLAGS='-O2', CXXFLAGS='-O2', CPPFLAGS='', LDFLAGS='-L' + str(sysroot / 'usr/pkg/gcc16/lib') + ' -Wl,-rpath,/usr/pkg/gcc16/lib -Wl,-z,relro')

    def configure(name, script, overrides=None):
        directory = work / 'build' / triplet / ('libstdc++-' + name)
        directory.mkdir(parents=True)
        run('configure-' + name, [script] + configure_args, directory=directory, extra=dict(configure_env, **(overrides or {})))
        return directory

    base = configure('base', baseline / 'libstdc++-v3/configure')
    current = configure('current', source / 'libstdc++-v3/configure')
    for directory in (base, current):
        run('headers-' + directory.name, [make, '-C', 'include', 'all'], directory=directory)

    def compile_args(directory):
        return [cxx] + flags + ['-nostdinc++', '-I' + str(directory / 'include' / triplet), '-I' + str(directory / 'include'), '-I' + str(source / 'libstdc++-v3/libsupc++'), '-std=gnu++23']

    fixture = here / 'imports.cc'
    run('global-declarations', compile_args(base) + ['-DGLOBAL_MATH_NAMES', '-c', fixture, '-o', work / 'globals.o'])
    error = run('std-imports-before', compile_args(base) + ['-fsyntax-only', fixture], 1)
    require('not a member' in error, 'Baseline failed for an unrelated reason')
    run('std-imports', compile_args(current) + ['-Wall', '-Wextra', '-Werror', '-c', fixture, '-o', work / 'imports.o'])
    symbols = [line.split()[-1] for line in capture([tools['NM'], '-u', work / 'imports.o'], env).splitlines() if line.split()]
    require(set(names).issubset(symbols), 'Missing literal math relocations')
    link = ['-L' + str(sysroot / 'usr/pkg/gcc16/lib'), '-Wl,-rpath,/usr/pkg/gcc16/lib', '-Wl,-rpath-link,' + str(sysroot / 'usr/lib'), '-lm']
    run('std-link', [cxx] + flags + [work / 'imports.o'] + link + ['-o', work / 'math-consumer'])
    module_inputs = {name: (source / 'libstdc++-v3/src/c++23' / (name + '.in')).read_bytes() + (source / 'libstdc++-v3/src/c++23/std-clib.cc.in').read_bytes() for name in ('std.cc', 'std.compat.cc')}
    modules = work / 'modules'
    modules.mkdir()
    for name, data in module_inputs.items():
        (modules / name).write_bytes(data)
    module_flags = ['-fmodules', '-isystem', source / 'libstdc++-v3/include/backward']
    run('full-std-before', compile_args(base) + module_flags + ['-c', modules / 'std.cc', '-o', modules / 'before.o'], 1, modules)
    for name in module_inputs:
        run(name, compile_args(current) + module_flags + ['-c', modules / name, '-o', modules / (name + '.o')], directory=modules)
        require((modules / 'gcm.cache' / (name.removesuffix('.cc') + '.gcm')).stat().st_size > 1024 and (modules / (name + '.o')).stat().st_size > 0, 'Missing real module BMI')
    for name, selection in {'std': '-DMATH_STD_MODULE', 'compat': '-DMATH_COMPAT_MODULE'}.items():
        mode = ['-DGLOBAL_MATH_NAMES'] if name == 'compat' else []
        run('module-import-' + name, compile_args(current) + module_flags + [selection] + mode + [fixture, modules / 'std.cc.o', modules / 'std.compat.cc.o'] + link + ['-o', modules / (name + '-consumer')], directory=modules)
    require(all((modules / name).read_bytes() == data for name, data in module_inputs.items()), 'Module sources were replaced')
    fault_header = work / 'missing-declaration'
    fault_header.mkdir()
    math = (sysroot / 'usr/include/math.h').read_text()
    require(re.search(r'\bacosf\b', math), 'No target acosf declaration')
    (fault_header / 'math.h').write_text(re.sub(r'\bacosf\b', 'absent_declaration_acosf', math))
    no_decl = configure('missing-declaration', source / 'libstdc++-v3/configure', {'CPPFLAGS': '-I' + str(fault_header)})
    require(not re.search(r'^#define HAVE_ACOSF 1$', (no_decl / 'config.h').read_text(), re.M), 'Missing declaration became available')
    fault_lib = work / 'missing-symbol'
    fault_lib.mkdir()
    libm = sysroot / 'usr/lib/libm.a'
    members = sorted(set(re.findall(r'^.*:([^:\s]+):.* [TW] acosf\s*$', capture([tools['NM'], '-A', '--defined-only', libm], env), re.M)))
    require(members, 'Cannot identify the real acosf archive member')
    shutil.copy2(libm, fault_lib / 'libm.a')
    (fault_lib / 'libm.a').chmod(0o644)
    run('remove-symbol', [tools['AR'], 'd', fault_lib / 'libm.a'] + members)
    no_symbol = configure('missing-symbol', source / 'libstdc++-v3/configure', {'LDFLAGS': '-L' + str(fault_lib) + ' ' + configure_env['LDFLAGS']})
    require(not re.search(r'^#define HAVE_ACOSF 1$', (no_symbol / 'config.h').read_text(), re.M), 'Missing symbol became available')
    fault_cap = work / 'missing-capability' / triplet / 'bits'
    fault_cap.mkdir(parents=True)
    config = (current / 'include' / triplet / 'bits/c++config.h').read_text()
    require(len(re.findall(r'^#define _GLIBCXX_HAVE_ACOSF 1$', config, re.M)) == 1, 'Missing positive capability')
    (fault_cap / 'c++config.h').write_text(re.sub(r'^#define _GLIBCXX_HAVE_ACOSF 1$', '/* deliberately absent for the negative test */', config, flags=re.M))
    negative = compile_args(current)
    negative.insert(4, '-I' + str(work / 'missing-capability' / triplet))
    run('removed-capability', negative + ['-fsyntax-only', fixture], 1)
    jsonio.write_json(work / 'acceptance.json', {'target': target, 'names': names, 'full_modules': {name: hashlib.sha256(data).hexdigest() for name, data in module_inputs.items()}, 'target_execution': False, 'package_lifecycle': False, 'results': len(results)})
    print('PASS: 43 target math declarations/imports/links, complete std/std.compat and three capability negatives; target execution remains separate')


if __name__ == '__main__':
    try:
        sdk_source.install_signal_handlers()
        main(sys.argv[1:])
    except Exception as error:
        print('cross-math: ' + str(error), file=sys.stderr)
        status = getattr(error, 'returncode', None)
        sys.exit((128 - status if status < 0 else status) if status else 2)
