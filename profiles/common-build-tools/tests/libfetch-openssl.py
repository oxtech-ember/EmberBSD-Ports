#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise real pkgsrc metadata for both libfetch OpenSSL options."""
import subprocess
import sys
from pathlib import Path

if len(sys.argv) != 4:
    raise SystemExit('usage: libfetch-openssl.py BMAKE PKGSRC MAKECONF')
bmake, tree, makeconf = sys.argv[1:]
if not all(Path(p).is_absolute() for p in (bmake, tree, makeconf)):
    raise SystemExit('absolute paths required')
for options, wanted in [('inet6 openssl', True), ('inet6', False)]:
    command = [bmake, '-C', str(Path(tree) / 'net/fetch'), 'MAKECONF=' + makeconf,
               'PKG_BUILD_OPTIONS.libfetch=' + options, '-V', '${DEPENDS}']
    result = subprocess.run(command, text=True, capture_output=True, check=True)
    present = 'openssl>=3:../../security/openssl' in result.stdout.split()
    if present != wanted:
        raise SystemExit('unexpected OpenSSL dependency for ' + options + ': ' + result.stdout)
admin = Path(bmake).parent.parent / 'sbin/pkg_admin'
for version, accepted in [('openssl-1.1.1', False), ('openssl-3.6.5', True)]:
    result = subprocess.run([str(admin), 'pmatch', 'openssl>=3', version], capture_output=True)
    if (result.returncode == 0) != accepted:
        raise SystemExit('unexpected OpenSSL version acceptance: ' + version)
print('PASS: libfetch OpenSSL dependency follows options and requires ABI 3')
