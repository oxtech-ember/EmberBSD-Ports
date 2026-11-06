#!/usr/bin/env python3
"""Test synthetic server paths from built MIT libraries; no KDC is started."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

p = argparse.ArgumentParser()
p.add_argument('--source', type=Path, required=True, help='configured krb5 src')
p.add_argument('--cc', type=Path, required=True, help='selected native SDK compiler')
p.add_argument('--runtime-prefix', type=Path, required=True, help='relocated trial prefix with lib and synthetic config')
p.add_argument('--work', type=Path, required=True)
p.add_argument('--db-relative', required=True, help='configured prefix-relative default DB')
p.add_argument('--acl-relative', required=True, help='configured prefix-relative default ACL')
a = p.parse_args()
if sys.platform != 'darwin':
    p.error('this fixture uses the Darwin dynamic loader')
if not a.cc.is_absolute() or not a.cc.is_file():
    p.error('supply the selected SDK compiler as an absolute path')
for value in (a.db_relative, a.acl_relative):
    if Path(value).is_absolute() or '..' in Path(value).parts:
        p.error('default paths must be prefix-relative and contain no ..')
a.work.mkdir(parents=True, exist_ok=True)
exe = a.work / 'server-paths'
subprocess.run([str(a.cc), '-I' + str(a.source / 'include'),
                str(Path(__file__).with_name('params.c')),
                '-L' + str(a.source / 'lib/.libs'), '-lkadm5srv_mit', '-lkrb5',
                '-o', str(exe)], check=True, timeout=60)
env = dict(os.environ)
env['DYLD_LIBRARY_PATH'] = str(a.runtime_prefix / 'lib')
env.pop('KRB5_CONFIG', None)
env.pop('KRB5_KDC_PROFILE', None)
def run(*args):
    return subprocess.run([str(exe), *args], env=env, check=True,
                          text=True, capture_output=True, timeout=15).stdout.splitlines()
expected = [str(a.runtime_prefix / a.db_relative), str(a.runtime_prefix / a.acl_relative)]
actual = run()
if actual != expected:
    raise SystemExit('default mismatch: expected %r, got %r' % (expected, actual))
actual = run('explicit')
if actual != ['/tmp/explicit-db', '/tmp/explicit-acl']:
    raise SystemExit('explicit mismatch: %r' % (actual,))
print('PASS: compiled defaults relocate, explicit server parameters retained')
