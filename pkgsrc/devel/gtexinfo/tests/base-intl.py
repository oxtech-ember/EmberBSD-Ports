#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Exercise the optional checked base libintl with a real target linker."""
import argparse
import os
from pathlib import Path
import subprocess

p = argparse.ArgumentParser(description=__doc__)
for name in ('source', 'work', 'shell', 'cc', 'ld', 'sysroot'):
    p.add_argument('--' + name, type=Path, required=True)
p.add_argument('--build', required=True)
p.add_argument('--host', required=True)
a = p.parse_args()
if a.work.exists() or not a.work.is_absolute():
    p.error('work must be a new absolute directory')
a.work.mkdir()
empty = a.work / 'without-intl'
empty.mkdir()
target = [str(a.cc), '--target=' + a.host, '--sysroot=' + str(a.sysroot),
          '--ld-path=' + str(a.ld)]
subprocess.run([*target, '-shared', '-nostdlib', '-x', 'c', '-', '-o', str(empty / 'libintl.so')],
               input='', text=True, check=True)
env = dict(os.environ, CONFIG_SHELL=str(a.shell), SHELL=str(a.shell),
           CC=' '.join(target), LD=str(a.ld), LC_ALL='C')
base = [str(a.shell), str(a.source / 'configure'), '--build=' + a.build,
        '--host=' + a.host, '--disable-perl-tools', '--disable-perl-xs', '--with-base-libintl']
for name, flags, success in (('available', '', True), ('missing', '-L' + str(empty), False)):
    obj = a.work / name
    obj.mkdir()
    result = subprocess.run(base, cwd=obj, env=dict(env, LDFLAGS=flags), capture_output=True, text=True)
    log = result.stdout + result.stderr
    (a.work / (name + '.log')).write_text(log)
    if (result.returncode == 0) != success:
        raise SystemExit(name + ' configure returned ' + str(result.returncode))
    if success:
        config = (obj / 'config.h').read_text()
        makefile = (obj / 'Makefile').read_text()
        assert '#define ENABLE_NLS 1' in config and 'LIBINTL = -lintl' in makefile
        assert 'INTLLIBS = -lintl' in makefile
        assert 'checking for the base libintl public API... yes' in log
    else:
        assert 'base libintl public API link failed' in log
print('checked base libintl configure: PASS')
