#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise the actual upstream Autoconf probes with real GCC16 compilers."""
import argparse
import os
from pathlib import Path
import shlex
import subprocess
import sys
sys.dont_write_bytecode = True
from sdk_source import load_sdk


def main():
    sdk, args = load_sdk()
    from emberbsd_sdk.inventory import sha256_file
    from emberbsd_sdk.jsonio import write_json
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('upstream-src', 'patched-src', 'autoconf', 'cc', 'native-cc', 'sysroot', 'work'):
        parser.add_argument('--' + name, required=True, type=Path)
    arg = parser.parse_args(args)
    paths = vars(arg)
    if any(not p.is_absolute() for p in paths.values()):
        raise ValueError('All paths must be absolute')
    if arg.work.exists():
        raise ValueError('Work must be unused')
    for p in (arg.cc, arg.native_cc):
        if subprocess.check_output([str(p), '-dumpfullversion'], text=True).strip() != '16.2.0':
            raise ValueError('Both compilers must be the common GCC16')
    arg.work.mkdir()
    results = []
    for case, source, host, compiler, flags, expected in (
        ('upstream-cross-refusal', arg.upstream_src, 'aarch64--netbsd', arg.cc, '', 'Cannot test for constructor/destructor'),
        ('netbsd-cross', arg.patched_src, 'aarch64--netbsd', arg.cc, '', None),
        ('unknown-cross-refusal', arg.patched_src, 'aarch64-unknown-freebsd', arg.cc, '', 'Cannot test for constructor/destructor'),
        ('missing-attribute-refusal', arg.patched_src, 'aarch64--netbsd', arg.cc, '-Dconstructor=ember_unknown_attribute', 'NetBSD ELF constructor/destructor link test failed'),
        ('wrong-platform-refusal', arg.patched_src, 'aarch64--netbsd', arg.cc, '-U__NetBSD__', 'NetBSD ELF constructor/destructor link test failed'),
        ('upstream-native', arg.upstream_src, 'x86_64-pc-linux-gnu', arg.native_cc, '', None),
        ('patched-native', arg.patched_src, 'x86_64-pc-linux-gnu', arg.native_cc, '', None),
    ):
        work = arg.work / case
        work.mkdir()
        aclocal = (source / 'aclocal.m4').read_text()
        start = aclocal.index('AC_DEFUN([KRB5_AC_GCC_ATTRS],')
        end = aclocal.index('AC_DEFUN([KRB5_AC_PRAGMA_WEAK_REF]', start)
        printf = (source / 'configure.ac').read_text()
        start_printf = printf.index('AC_MSG_CHECKING(for POSIX printf positional specification support)')
        end_printf = printf.index('# for t_locate_kdc test', start_printf)
        body = ('AC_INIT([mit-probe-contract], [1])\nAC_PROG_CC\n'
                + 'krb5_cv_host=' + shlex.quote(host) + '\n'
                + aclocal[start:end] + '\nKRB5_AC_GCC_ATTRS\n'
                + printf[start_printf:end_printf] + '\nAC_OUTPUT\n')
        (work / 'configure.ac').write_text(body)
        environment = os.environ.copy()
        environment['CC'] = str(compiler)
        environment['CONFIG_SITE'] = '/dev/null'
        environment['CFLAGS'] = flags
        if compiler == arg.cc:
            environment['CFLAGS'] += (' --sysroot=' + str(arg.sysroot) + ' -B' + str(arg.sysroot)
                + '/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0/')
        with (work / 'autoconf.log').open('wb') as log:
            subprocess.run([str(arg.autoconf)], cwd=work, env=environment, stdout=log, stderr=log, check=True, timeout=60)
        command = ['./configure', '--build=x86_64-pc-linux-gnu', '--host=' + host]
        with (work / 'configure.log').open('wb') as log:
            result = subprocess.run(command, cwd=work, env=environment, stdout=log, stderr=log, timeout=90)
        output = (work / 'configure.log').read_text()
        if (expected is None and (result.returncode != 0 or
                'constructor/destructor attribute support... yes,yes' not in output or
                'POSIX printf positional specification support... yes' not in output)) or (
                expected is not None and (result.returncode == 0 or expected not in output)):
            raise ValueError('Unexpected result: ' + case)
        results.append(dict(case=case, exit=result.returncode, expected=expected,
                            configure_sha256=sha256_file(work / 'configure')))
        print('PASS: ' + case, flush=True)
    write_json(arg.work / 'receipt.json', dict(sdk_source=sdk, tests=results,
        input_sha256={str(p):sha256_file(p.resolve(strict=True)) for p in (arg.cc, arg.native_cc,
        arg.upstream_src/'aclocal.m4', arg.upstream_src/'configure.ac',
        arg.patched_src/'aclocal.m4', arg.patched_src/'configure.ac')}))


if __name__ == '__main__':
    main()
