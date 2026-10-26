#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise configured Berkeley DB compiler commands with real libtool."""

import argparse
import ctypes
import os
from pathlib import Path
import shlex
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--makefile', type=Path, required=True)
    parser.add_argument('--host-prefix', type=Path, required=True)
    parser.add_argument('--wrapper-config', type=Path, required=True)
    parser.add_argument('--native-tools', type=Path, required=True,
                        help='SDK native-tool command mapping, including ar/ranlib')
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--expect-rejection', action='store_true')
    args = parser.parse_args()
    prefix = args.host_prefix.resolve(strict=True)
    makefile = args.makefile.resolve(strict=True)
    work = args.work.absolute()
    work.mkdir()
    wrapper_config = args.wrapper_config.resolve(strict=True)
    native_tools = args.native_tools.resolve(strict=True)
    env = dict(os.environ, CWRAPPERS_CONFIG_DIR=str(wrapper_config),
               PATH=os.pathsep.join([str(wrapper_config.parent / 'bin'), str(native_tools),
                   *(str(prefix / name) for name in ('bin', 'sbin', 'gnu/bin'))]))
    for name in ('CC', 'CXX', 'CPP', 'CFLAGS', 'CXXFLAGS', 'CPPFLAGS',
                 'LDFLAGS', 'MAKEFLAGS', 'MFLAGS'):
        env.pop(name, None)

    def command(role):
        result = subprocess.check_output(
            [str(prefix / 'bin/bmake'), '-f', str(makefile), '-V', '${' + role + '}'],
            cwd=makefile.parent, env=env, text=True)
        return shlex.split(result)

    def run(argv, expected=0):
        result = subprocess.run(argv, cwd=makefile.parent, env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        with (work / 'commands.log').open('ab') as log:
            log.write((shlex.join(argv) + '\n').encode())
            log.write(result.stdout)
        if result.returncode != expected:
            raise RuntimeError(f'command returned {result.returncode}, expected {expected}: {argv}')
        return result

    c = work / 'value.c'
    c.write_text('int value(void) { return 6 * 7; }\n')
    first = command('CC') + ['-c', str(c), '-o', str(work / 'value.lo')]
    if args.expect_rejection:
        result = subprocess.run(first, cwd=makefile.parent, env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (work / 'rejection.log').write_bytes(result.stdout)
        if result.returncode == 0 or b'unable to infer tagged configuration' not in result.stdout:
            raise RuntimeError('the baseline did not reproduce the libtool language inference failure')
        print('Baseline: actual configured C command rejects missing language tag')
        return
    run(first)
    run(command('SOLINK') + ['-rpath', str(prefix / 'lib'), '-o',
                            str(work / 'libvalue.la'), str(work / 'value.lo')])
    library = ctypes.CDLL(str(work / '.libs/libvalue.so'))
    if library.value() != 42:
        raise RuntimeError('C shared library returned the wrong value')

    cpp = work / 'value.cc'
    cpp.write_text('class Value { public: int get() const { return 42; } };\n'
                   'extern "C" int cxx_value() { Value value; return value.get(); }\n')
    run(command('CXX') + ['-c', str(cpp), '-o', str(work / 'value-cxx.lo')])
    run(command('XSOLINK') + ['-rpath', str(prefix / 'lib'), '-o',
                             str(work / 'libvalue_cxx.la'), str(work / 'value-cxx.lo')])
    cxx_library = ctypes.CDLL(str(work / '.libs/libvalue_cxx.so'))
    if cxx_library.cxx_value() != 42:
        raise RuntimeError('C++ shared library returned the wrong value')
    for language, compile_role, link_role in (('c', 'CC', 'CCLINK'),
                                              ('cc', 'CXX', 'CXXLINK')):
        source = work / ('main.' + language)
        source.write_text('int main(void) { return 42; }\n')
        obj = work / ('main-' + language + '.lo')
        executable = work / ('main-' + language)
        run(command(compile_role) + ['-c', str(source), '-o', str(obj)])
        run(command(link_role) + [str(obj), '-o', str(executable)])
        run([str(executable)], expected=42)
    print('Berkeley DB: C/C++ compile, executable links and shared-library calls passed')


if __name__ == '__main__':
    main()
