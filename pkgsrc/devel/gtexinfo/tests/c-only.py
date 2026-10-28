#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Configure both Texinfo modes, build the C-only tools and run registrar tests.

The caller selects all native commands and a prefix-only PATH. This test does
not install a package or execute target programs.
"""
import argparse
import os
from pathlib import Path
import subprocess

p = argparse.ArgumentParser(description=__doc__)
for name in ('source', 'work', 'shell', 'make', 'cc', 'ld', 'ar', 'ranlib', 'perl'):
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
for name in ('source', 'shell', 'make', 'cc', 'ld', 'ar', 'ranlib', 'perl'):
    value = getattr(a, name)
    if not value.is_absolute() or not value.exists():
        p.error(name + ' must be an existing absolute path')
if not a.work.is_absolute() or a.work.exists():
    p.error('work must be a new absolute path')
a.work.mkdir()
env = dict(os.environ, CONFIG_SHELL=str(a.shell), SHELL=str(a.shell),
           CC=str(a.cc), LD=str(a.ld), AR=str(a.ar), RANLIB=str(a.ranlib),
           MAKE=str(a.make), PATH_SEPARATOR=os.pathsep, LC_ALL='C')

def run(name, argv, cwd, *, expected=0, environment=env):
    with (a.work / (name + '.log')).open('wb') as log:
        result = subprocess.run(argv, cwd=cwd, env=environment, stdout=log, stderr=subprocess.STDOUT)
    if result.returncode != expected:
        raise SystemExit(f'{name}: exit {result.returncode}, expected {expected}; see {log.name}')

source = a.source.resolve(strict=True)
c_only = a.work / 'c-only'
c_only.mkdir()
without_perl = dict(env, PERL=str(a.work / 'no-perl'))
run('c-only-configure', [str(a.shell), str(source / 'configure'), '--disable-perl-tools',
     '--disable-perl-xs', '--disable-nls'], c_only, environment=without_perl)
if (c_only / 'tta').exists():
    raise SystemExit('C-only mode configured tta')
config_log = (a.work / 'c-only-configure.log').read_text()
if 'checking Perl version and modules' in config_log or 'configuring in tta' in config_log:
    raise SystemExit('C-only mode ran a Perl or tta probe')
conflict = a.work / 'conflict'
conflict.mkdir()
run('conflicting-options', [str(a.shell), str(source / 'configure'), '--disable-perl-tools',
    '--enable-perl-xs'], conflict, expected=1, environment=without_perl)
if 'Perl tools cannot be enabled' not in (a.work / 'conflicting-options.log').read_text():
    raise SystemExit('conflicting options were not diagnosed')
run('c-only-build', [str(a.make), '-j2'], c_only, environment=without_perl)
for path in ('info/ginfo', 'install-info/ginstall-info'):
    if not (c_only / path).is_file():
        raise SystemExit('C-only build did not produce ' + path)
run('registrar-check', [str(a.make), '-C', str(c_only / 'install-info'), 'check'], c_only,
    environment=without_perl)
full = a.work / 'full'
full.mkdir()
run('full-configure', [str(a.shell), str(source / 'configure'), '--disable-perl-xs', '--disable-nls'],
    full, environment=dict(env, PERL=str(a.perl)))
if not (full / 'tta/config.status').is_file():
    raise SystemExit('default full mode did not configure tta')
full_log = (a.work / 'full-configure.log').read_text()
if any(message in full_log for message in ('awk: inaccessible', 'awk: not found',
                                             'awk: command not found', 'LLVM ERROR:')):
    raise SystemExit('full configure reported a failed host tool')
print('PASS: C-only tools, registrar checks and default full configure')
