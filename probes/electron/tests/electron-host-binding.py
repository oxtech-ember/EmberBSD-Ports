#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Exercise Electron-generated makeconf through actual pkgsrc cwrappers."""
import argparse
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
for name in ('pkgsrc', 'makeconf', 'binding', 'bmake', 'host-prefix', 'work'):
    parser.add_argument('--' + name, type=Path, required=True)
a = parser.parse_args()
for path in (a.pkgsrc, a.makeconf, a.binding, a.bmake, a.host_prefix, a.work):
    if not path.is_absolute(): parser.error('all paths must be absolute')
if a.work.exists(): parser.error('work directory must be new')
a.work.mkdir(parents=True)
probe = a.work / 'probe.cc'
probe.write_text('int main() { return 0; }\n')
makeconf = a.makeconf
env = {'PATH': str(a.host_prefix / 'bin') + ':' + str(a.host_prefix / 'gnu/bin'),
       'HOME': os.environ.get('HOME', str(a.work)), 'LC_ALL': 'C', 'MAKECONF': str(makeconf)}
args = [str(a.bmake), '-C', str(a.pkgsrc / 'pkgtools/digest'), 'USE_CROSS_COMPILE=no',
        'USE_LANGUAGES=c c++', 'DEPENDS_TARGET=emberbsd-clang-wrapper-missing-dependency',
        'WRKOBJDIR=' + str(a.work / 'objects')]
def run(command, **kw):
    return subprocess.run(command, env=env, check=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, **kw)
wrkdir = Path(run(args + ['show-var', 'VARNAME=WRKDIR']).stdout.decode().strip())
run(args + ['wrapper'])
config = wrkdir / '.cwrapper/config'
env['CWRAPPERS_CONFIG_DIR'] = str(config)
env['CWRAPPERS_EMIT_ARGV'] = '1'
for wrapper, role in (('cc', 'cc'), ('c++', 'cxx'), ('cpp', 'cpp')):
    result = run([str(wrkdir / '.cwrapper/bin' / wrapper), '-c', str(probe)]).stdout
    if not result.endswith(b'\0'): raise AssertionError('wrapper emitted incomplete argv')
    actual = Path(os.fsdecode(result.split(b'\0', 1)[0]))
    expected = a.binding / role
    if not os.path.samefile(actual, expected):
        raise AssertionError(f'{wrapper} chose {actual}; expected SDK binding {expected}')
print('PASS: Electron makeconf cwrappers select all SDK bindings')
