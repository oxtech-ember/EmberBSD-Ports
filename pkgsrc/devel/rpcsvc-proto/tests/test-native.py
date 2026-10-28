#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check the installed rpcgen and its generated protocol headers.

Usage: test-native.py --prefix PREFIX --cc ABSOLUTE_C_COMPILER
"""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser()
p.add_argument('--prefix', required=True)
p.add_argument('--cc', required=True)
args = p.parse_args()
prefix = Path(args.prefix)
rpcgen = prefix / 'bin/rpcgen'
for path in (rpcgen, Path(args.cc)):
    if not path.is_absolute() or not os.access(path, os.X_OK):
        p.error('select executables by absolute path: ' + str(path))
# On Darwin the headers must not shadow the macOS SDK <rpcsvc/*.h>
# through -I PREFIX/include.
include = prefix / 'include'
if os.uname().sysname == 'Darwin':
    shadow = sorted(path.name for path in (include / 'rpcsvc').glob('*.x'))
    if shadow:
        raise SystemExit('FAIL: rpcsvc headers in the default include path: ' + ', '.join(shadow))
    include = include / 'rpcsvc-proto'
# The package generates these headers with its own rpcgen at build time.
mount = (include / 'rpcsvc/mount.h').read_text()
if 'MOUNTPROG' not in mount or 'struct mountbody' not in mount:
    raise SystemExit('FAIL: installed rpcsvc/mount.h has no protocol definitions')
with tempfile.TemporaryDirectory(prefix='rpcgen-test-', dir=os.environ.get('TMPDIR')) as work:
    work = Path(work)
    cpp = work / 'cpp'
    cpp.write_text('#!/bin/sh\nexec %s -E "$@"\n' % args.cc)
    cpp.chmod(0o755)
    source = work / 'ember.x'
    source.write_text('struct ember_pair { int left; int right; };\n'
                      'program EMBER_PROG { version EMBER_VERS {\n'
                      '  int EMBER_SUM(ember_pair) = 1; } = 1; } = 0x20000001;\n')
    for option, name, expected in (('-h', 'ember.h', 'struct ember_pair'),
                                   ('-c', 'ember_xdr.c', 'xdr_ember_pair')):
        output = work / name
        # -b selects the code that pkgsrc requests for NetBSD targets.
        subprocess.run([str(rpcgen), '-b', '-Y', str(work), option, '-o', str(output), str(source)],
                       check=True, cwd=work)
        if expected not in output.read_text():
            raise SystemExit('FAIL: rpcgen %s output lacks %s' % (option, expected))
print('PASS: installed rpcgen generates headers and XDR code')
