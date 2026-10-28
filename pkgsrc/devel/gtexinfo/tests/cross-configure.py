#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Check Texinfo cross configure routes C-only and native-tool failures.

Use the actual selected cross compiler and linker and prefix-only PATH. The
control deliberately selects a missing native compiler to check failure
propagation; it never executes a target program.
"""
import argparse
import os
from pathlib import Path
import subprocess

p = argparse.ArgumentParser(description=__doc__)
for name in ('source', 'work', 'shell', 'make', 'cross-cc', 'cross-ld', 'ar', 'ranlib', 'native-cc', 'native-ld', 'perl'):
    p.add_argument('--' + name, type=Path, required=True)
p.add_argument('--build', required=True)
p.add_argument('--host', required=True)
a = p.parse_args()
for name in ('source', 'shell', 'make', 'cross_cc', 'cross_ld', 'ar', 'ranlib', 'native_cc', 'native_ld', 'perl'):
    value = getattr(a, name)
    if not value.is_absolute() or not value.exists():
        p.error(name + ' must be an existing absolute path')
if not a.work.is_absolute() or a.work.exists():
    p.error('work must be a new absolute path')
a.work.mkdir()
env = dict(os.environ, CONFIG_SHELL=str(a.shell), SHELL=str(a.shell),
           CC=str(a.cross_cc), LD=str(a.cross_ld), AR=str(a.ar), RANLIB=str(a.ranlib),
           BUILD_CC=str(a.work / 'missing-native-cc'), BUILD_AR=str(a.ar),
           BUILD_RANLIB=str(a.ranlib), LD_FOR_BUILD=str(a.native_ld),
           MAKE=str(a.make), PERL=str(a.perl), PATH_SEPARATOR=os.pathsep, LC_ALL='C')
base = [str(a.shell), str(a.source / 'configure'), '--build=' + a.build,
        '--host=' + a.host, '--disable-perl-xs', '--disable-nls']

def run(name, extra, environment=env):
    work = a.work / name
    work.mkdir()
    result = subprocess.run([*base, *extra], cwd=work, env=environment, capture_output=True, text=True)
    text = result.stdout + result.stderr
    (a.work / (name + '.log')).write_text(text)
    return result, text

result, log = run('c-only', ['--disable-perl-tools'])
if result.returncode or 'Doing configure of native tools' in log or 'checking Perl version and modules' in log:
    raise SystemExit('C-only cross configure failed or entered native Perl tools')
result, log = run('full-missing-native-cc', [])
if (result.returncode == 0 or 'Doing configure of native tools' not in log or
        'C compiler cannot create executables' not in log or 'Continuing with main configure' in log):
    raise SystemExit('full cross configure did not propagate the native compiler failure')
native = dict(env, BUILD_CC=str(a.native_cc), CPPFLAGS_FOR_BUILD='-DEMBER_TEST_HOST_CPP=1',
              CFLAGS_FOR_BUILD='-DEMBER_TEST_HOST_CC=1', LDFLAGS_FOR_BUILD='-L' + str(a.work),
              LIBS_FOR_BUILD='-lm')
result, log = run('full-native-abi', [], environment=native)
if result.returncode or 'Continuing with main configure' not in log:
    raise SystemExit('full cross configure with selected native ABI failed')
if any(message in log for message in ('awk: inaccessible', 'awk: not found',
                                       'awk: command not found', 'LLVM ERROR:')):
    raise SystemExit('full cross configure reported a failed host tool')
config = (a.work / 'full-native-abi/tools/config.log').read_text()
for flag in ('-DEMBER_TEST_HOST_CPP=1', '-DEMBER_TEST_HOST_CC=1', '-L' + str(a.work), '-lm'):
    if flag not in config:
        raise SystemExit('nested native configure lost ' + flag)
print('PASS: C-only cross, native failure propagation and explicit native ABI flags')
