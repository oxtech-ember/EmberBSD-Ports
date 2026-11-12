#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Check actual native and target gpg-error recipe metadata."""
import argparse
import os
import subprocess
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
for name in ('pkgsrc', 'makeconf', 'bmake'):
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
env = dict(os.environ, MAKECONF=str(a.makeconf))
def query(role, *extra):
    result = subprocess.run([str(a.bmake), '-C', str(a.pkgsrc / 'security/libgpg-error'),
                             'USE_CROSS_COMPILE=' + role, *extra, 'show-vars',
                             'VARNAMES=OPSYS PKGREVISION SUBST_CLASSES EMBER_SYSCONF_RELATIVE PREFIX'], env=env,
                            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return result.stdout.splitlines()
native, target = query('no'), query('yes')
assert native[:2] == ['Darwin', '1'] and 'ember-reloc' in native[2].split(), native
assert target[:2] == ['NetBSD', '1'] and 'ember-reloc' not in target[2].split(), target
prefix = Path(native[4])
for selected, expected in ((str(prefix / 'etc'), '../etc'),
                           (str(prefix / 'custom'), '../custom'),
                           ('/etc/gnupg', '/etc/gnupg')):
    values = query('no', 'PKG_SYSCONFDIR=' + selected)
    assert values[3] == expected, values
print('PASS native/target revision and sysconf layout selection')
