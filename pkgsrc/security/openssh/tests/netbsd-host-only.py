#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check the native ssh HOST_ONLY auth object against server-only symbols."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
for name in ('source', 'build', 'prefix', 'cc', 'nm', 'work-dir'):
    parser.add_argument('--' + name, type=Path, required=True)
args = parser.parse_args()
assert all(value.is_absolute() for value in vars(args).values())
with tempfile.TemporaryDirectory(dir=args.work_dir) as directory:
    for host in (False, True):
        obj = Path(directory) / ('host.o' if host else 'server.o')
        cmd = [str(args.cc), '-DHAVE_CONFIG_H', '-c', '-I', str(args.source),
               '-I', str(args.build), '-I', str(args.build / 'openbsd-compat/include'),
               '-I', str(args.prefix / 'include'), str(args.source / 'auth.c'), '-o', str(obj)]
        if host:
            cmd.insert(1, '-DHOST_ONLY')
        subprocess.run(cmd, check=True, env=dict(os.environ))
        symbols = subprocess.run([str(args.nm), str(obj)], check=True,
                                 capture_output=True, text=True).stdout.splitlines()
        names = {line.split()[-1].lstrip('_') for line in symbols if line.split()}
        if host:
            assert not names.intersection({'options', 'auth_opts', 'includes', 'privsep_pw'})
            assert {'auth_debug_add', 'auth_debug_send', 'auth_debug_reset',
                    'auth_get_canonical_hostname'} <= names
        else:
            assert {'allowed_user', 'fakepw'} <= names
print('PASS: host-only auth excludes server globals and retains client utilities')
