#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); exercise upstream cross TLS probes and objects.
"""Configure GCC16 libstdc++ and compile its original call_once implementation."""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
import hashlib
import json
import os
import re
import shutil

PROFILE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROFILE / 'runtime/recipe/files'))
import sdk_source
sys.path.insert(0, str(PROFILE))


def main(arguments):
    args = sdk_source.arguments(arguments)
    from emberbsd_sdk import jsonio, process
    from host import TARGETS, VERSION, audit_patches, build_path, new_path, require, capture, logged
    require(len(args) == 6,
            'Usage: check.py TARGET PKGSRC PREPARED_GCC_SOURCE GCC16_PREFIX SYSROOT NEW_WORK --sdk-source SOURCE')
    target, *values = args
    require(target in TARGETS, 'Unknown target')
    tree, source, prefix, sysroot, work = [build_path(value) for value in values]
    new_path(work)
    triplet = TARGETS[target][0]
    make = os.environ.get('GNU_MAKE', '/usr/bin/make')
    gcc = prefix / 'bin' / (triplet + '-gcc')
    env = {'PATH': str(prefix / 'bin') + ':' + os.environ.get('PATH', '')}
    require(capture([gcc, '-dumpfullversion'], env).strip() == VERSION
            and capture([gcc, '-dumpmachine'], env).strip() == triplet, 'GCC16 target required')
    compiler_info = process.capture([str(gcc), '-v'], env=process.sanitized_environment())
    require(re.search(rb'^Thread model: posix$', compiler_info.stderr, re.M),
            'The standalone source regression requires the POSIX application compiler')
    require(capture([make, '--version'], env).startswith('GNU Make '), 'GNU make required')
    audit_patches(tree / 'lang/gcc16')
    delta = tree / 'lang/gcc16/patches/patch-libstdc++-v3_configure_tls'
    work.mkdir()
    results = []

    def run(label, command, directory=work, extra=None):
        command = [str(arg) for arg in command]
        log = work / (label + '.log')
        logged(command, log, dict(env, **(extra or {})), directory)
        results.append({'name': label, 'argv': command, 'directory': str(directory),
                        'log_sha256': hashlib.sha256(log.read_bytes()).hexdigest()})
        jsonio.write_json(work / 'commands.json', results,
                          exclusive=not (work / 'commands.json').exists())

    baseline = work / 'baseline/libstdc++-v3'
    baseline.mkdir(parents=True)
    shutil.copy2(source / 'libstdc++-v3/configure', baseline / 'configure')
    run('reverse-tls-only', ['patch', '-f', '-R', '-F', '0', '-p0', '-i', delta],
        baseline.parent)
    flags = ['--sysroot=' + str(sysroot),
             '-B' + str(sysroot / 'usr/pkg/gcc16/lib/gcc' / triplet / VERSION) + '/',
             '-B' + str(sysroot / 'usr/pkg/gcc16/lib') + '/']
    tools = {name.upper(): str(prefix / 'bin' / (triplet + '-' + name))
             for name in 'ar as ld nm objcopy objdump ranlib readelf strip'.split()}
    build_triplet = capture(['sh', source / 'config.guess'], env).strip()
    gthreads = work / 'build' / triplet / 'libgcc'
    gthreads.mkdir(parents=True)
    (gthreads / 'gthr-default.h').symlink_to(source / 'libgcc/gthr-posix.h')
    configure_args = [
        '--srcdir=' + str(source / 'libstdc++-v3'), '--build=' + build_triplet,
        '--host=' + triplet, '--target=' + triplet, '--with-cross-host=' + build_triplet,
        '--with-target-subdir=' + triplet, '--prefix=/usr/pkg/gcc16',
        '--libdir=/usr/pkg/gcc16/lib', '--with-toolexeclibdir=/usr/pkg/gcc16/lib',
        '--with-gxx-include-dir=/usr/pkg/gcc16/include/c++', '--with-sysroot=' + str(sysroot),
        '--with-gnu-as', '--with-gnu-ld', '--with-as=' + tools['AS'], '--with-ld=' + tools['LD'],
        '--disable-multilib', '--enable-shared', '--enable-threads=posix', '--enable-long-long',
        '--disable-libssp', '--disable-libstdcxx-pch', '--disable-nls', '--disable-year2038',
        '--cache-file=/dev/null',
    ]
    configure_env = dict(
        tools, CC=' '.join([str(gcc)] + flags),
        CXX=' '.join([str(gcc)] + flags + ['-shared-libgcc', '-nostdinc++']),
        CFLAGS='-O2', CXXFLAGS='-O2', CPPFLAGS='',
        LDFLAGS='-L' + str(sysroot / 'usr/pkg/gcc16/lib') + ' -Wl,-rpath,/usr/pkg/gcc16/lib -Wl,-z,relro')

    def configure(name, script, changes=None):
        directory = work / 'build' / triplet / ('libstdc++-' + name)
        directory.mkdir()
        run('configure-' + name, [script] + configure_args, directory,
            dict(configure_env, **(changes or {})))
        return directory

    base = configure('before', baseline / 'configure')
    current = configure('after', source / 'libstdc++-v3/configure')
    require('#define HAVE_TLS 1' not in (base / 'config.h').read_text(),
            'Baseline unexpectedly has TLS capability')
    require(re.findall(r'^#define HAVE_TLS 1$', (current / 'config.h').read_text(), re.M) == ['#define HAVE_TLS 1'],
            'The real target TLS link probe did not succeed')
    # Reject only compiler inputs that exercise TLS. All other configure
    # probes still use the same real target compiler without cache answers.
    fault = work / 'reject-tls'
    fault.write_text('#!' + sys.executable + '\nimport os,sys\nfrom pathlib import Path\n'
                     'for name in sys.argv[1:]:\n'
                     ' p=Path(name)\n'
                     ' if p.is_file() and p.suffix in (".c",".cc",".cpp") and b"__thread" in p.read_bytes():\n'
                     '  print("intentional TLS compiler refusal",file=sys.stderr);sys.exit(1)\n'
                     'os.execv(' + repr(str(gcc)) + ',[' + repr(str(gcc)) + ']+sys.argv[1:])\n')
    fault.chmod(0o755)
    negative = configure('tls-link-refused', source / 'libstdc++-v3/configure',
                         {'CC': ' '.join([str(fault)] + flags)})
    require('#define HAVE_TLS 1' not in (negative / 'config.h').read_text()
            and 'intentional TLS compiler refusal' in (negative / 'config.log').read_text(),
            'Failed TLS compilation became a positive capability')
    inventories = {}
    for name, directory in (('before', base), ('after', current)):
        run('headers-' + name, [make, '-C', 'include', 'all'], directory)
        run('mutex-' + name, [make, '-C', 'src/c++11', 'mutex.lo', 'compatibility-thread-c++0x.lo'],
            directory)
        objects = []
        for item in ('mutex', 'compatibility-thread-c++0x'):
            metadata = (directory / 'src/c++11' / (item + '.lo')).read_text()
            candidates = re.findall(r"^(?:pic_object|non_pic_object)='([^']+)'$", metadata, re.M)
            require(candidates, 'Missing upstream libtool object selection')
            relative = Path(candidates[0])
            require(not relative.is_absolute() and '..' not in relative.parts,
                    'Unexpected upstream libtool object path')
            objects.append(directory / 'src/c++11' / relative)
        output = capture([tools['READELF'], '-Ws'] + objects, env)
        (work / ('symbols-' + name + '.txt')).write_text(output)
        inventories[name] = dict(
            tls_symbols={symbol: bool(re.search(r'\bTLS\s+GLOBAL\s+DEFAULT\s+\d+\s+' + symbol + r'\s*$', output, re.M))
                         for symbol in ('_ZSt11__once_call', '_ZSt15__once_callable')},
            legacy_functor=bool(re.search(r'\bOBJECT\s+GLOBAL\s+DEFAULT\s+\d+\s+_ZSt14__once_functor\s*$', output, re.M)),
            source_sha256={item: hashlib.sha256((source / 'libstdc++-v3/src/c++11' / item).read_bytes()).hexdigest()
                           for item in ('mutex.cc', 'compatibility-thread-c++0x.cc')})
    require(not any(inventories['before']['tls_symbols'].values())
            and inventories['before']['legacy_functor'], 'Wrong baseline call_once ABI')
    require(all(inventories['after']['tls_symbols'].values()), 'TLS call_once definitions are missing')
    require(inventories['before']['source_sha256'] == inventories['after']['source_sha256'],
            'The regression changed upstream C++ implementation sources')
    jsonio.write_json(work / 'result.json', dict(
        target=target, qualification='cross-configured-and-compiled-upstream-objects',
        execution_acceptance='not-run', abi=inventories,
        consumer_boundary='Rebuild non-TLS consumers; old binary compatibility is not qualified.'))
    print('PASS: real cross TLS detection, failed-link refusal and upstream call_once objects; target execution remains separate')


if __name__ == '__main__':
    try:
        sdk_source.install_signal_handlers()
        main(sys.argv[1:])
    except Exception as error:
        print(str(error), file=sys.stderr)
        status = getattr(error, 'returncode', None)
        sys.exit((128 - status if status < 0 else status) if status else 2)
