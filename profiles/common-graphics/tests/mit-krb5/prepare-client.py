#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Build bounded installed MIT Kerberos/GSS clients with the common GCC16."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
sys.dont_write_bytecode = True
from sdk_source import load_sdk


def main():
    sdk_source, args = load_sdk()
    from emberbsd_sdk.inventory import sha256_file
    from emberbsd_sdk.jsonio import write_json
    from emberbsd_sdk.elf import read_elf_dynamic
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('cross-tools', 'sysroot', 'work'):
        parser.add_argument('--' + name, required=True, type=Path)
    arg = parser.parse_args(args)
    if any(not p.is_absolute() for p in vars(arg).values()) or arg.work.exists():
        raise ValueError('Absolute inputs and unused work are required')
    cc = arg.cross_tools / 'bin/aarch64--netbsd-gcc'
    if subprocess.check_output([str(cc), '-dumpfullversion'], text=True).strip() != '16.2.0':
        raise ValueError('The common GCC16 is required')
    prefix = arg.sysroot / 'usr/pkg'
    for package in ('mit-krb5-1.22.2nb2', 'mit-krb5-devel-1.22.2nb2'):
        if not (prefix / 'pkgdb' / package / '+CONTENTS').is_file():
            raise ValueError('Install matching ordinary runtime and SDK packages first')
    owner = Path(__file__).resolve().parent
    sources = [owner / p for p in ('client.c', 'constructor.c', 'printf.c', 'unload.c', 'run.sh')]
    sonames = ('libkrb5.so.3', 'libgssapi_krb5.so.2', 'libk5crypto.so.3', 'libcom_err.so.3', 'libkrb5support.so.0')
    libraries = [prefix / 'lib' / n for n in sonames]
    inputs = [*sources, *libraries, cc]
    initial = {str(p):sha256_file(p.resolve(strict=True)) for p in inputs}
    readelf = arg.cross_tools / 'bin/aarch64--netbsd-readelf'
    for p in libraries:
        if read_elf_dynamic(p.resolve(strict=True), machine=183)['soname'] != p.name:
            raise ValueError('MIT library target or SONAME differs: ' + p.name)
        dynamic_text = subprocess.check_output([str(readelf), '-d', str(p)], text=True)
        if not any('(FLAGS_1)' in line and 'NODELETE' in line for line in dynamic_text.splitlines()):
            raise ValueError('MIT library lost its configured unload-prevention policy: ' + p.name)
    bundle = arg.work / 'bundle'
    (bundle / 'source').mkdir(parents=True)
    for p in sources:
        shutil.copyfile(p, bundle / (p.name if p.suffix == '.sh' else 'source/' + p.name))
    flags = ['--sysroot=' + str(arg.sysroot), '-B' + str(prefix) + '/gcc16/lib/gcc/aarch64--netbsd/16.2.0/',
             '-O2', '-g', '-Wall', '-Wextra', '-Werror', '-I' + str(prefix / 'include'),
             '-fsanitize=undefined', '-fsanitize-undefined-trap-on-error', '-fno-sanitize-recover=all']
    link = ['-L' + str(prefix / 'lib'), '-Wl,-rpath,/usr/pkg/lib', '-Wl,-rpath,/usr/pkg/gcc16/lib',
            '-Wl,-rpath-link,' + str(prefix / 'lib'), '-Wl,-rpath-link,' + str(prefix / 'gcc16/lib')]
    commands = []
    for name, source, extra in [('client', 'client.c', ['-lgssapi_krb5', '-lkrb5', '-lk5crypto', '-lcom_err', '-pthread']),
                                ('constructor', 'constructor.c', []), ('printf', 'printf.c', []), ('unload', 'unload.c', []),
                                ('constructor-no-attributes', 'constructor.c', ['-D__attribute__(x)='])]:
        command = [str(cc), *flags, str(bundle / 'source' / source), *link, *extra, '-o', str(bundle / name)]
        with (arg.work / (name + '.build.log')).open('wb') as log:
            subprocess.run(command, stdout=log, stderr=log, check=True, timeout=90)
        dynamic = read_elf_dynamic(bundle / name, machine=183)
        if any(str(p) in (dynamic['rpath'] or '') + (dynamic['runpath'] or '') for p in (arg.work, arg.sysroot)):
            raise ValueError('Build path leaked into runtime search path')
        commands.append(command)
    (bundle / 'libraries.sha256').write_text(''.join(initial[str(p)] + '  /usr/pkg/lib/' + p.name + '\n' for p in libraries))
    (bundle / 'krb5.conf').write_text('[libdefaults]\n dns_lookup_kdc = false\n dns_lookup_realm = false\n default_realm = EXAMPLE.INVALID\n')
    if initial != {str(p):sha256_file(p.resolve(strict=True)) for p in inputs}:
        raise ValueError('Input changed during client build')
    write_json(arg.work / 'receipt.json', dict(sdk_source=sdk_source, compiler=str(cc), input_sha256=initial, commands=commands))
    archive = arg.work / 'mit-krb5-clients.tgz'
    with tarfile.open(archive, 'w:gz') as output:
        output.add(bundle, arcname='.')
    print(sha256_file(archive), archive)


if __name__ == '__main__':
    main()
