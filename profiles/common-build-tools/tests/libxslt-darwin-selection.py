#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Check native and target libxslt package revisions with actual bmake."""
import argparse
import os
import subprocess
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
for name in ('pkgsrc', 'makeconf', 'bmake'):
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
env = dict(os.environ, MAKECONF=str(a.makeconf))
def query(role):
    out = subprocess.run([str(a.bmake), '-C', str(a.pkgsrc / 'textproc/libxslt'),
                          'USE_CROSS_COMPILE=' + role, 'show-vars',
                          'VARNAMES=OPSYS PKGREVISION'], env=env, check=True,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return out.stdout.splitlines()
assert query('no') == ['Darwin', '6']
assert query('yes') == ['NetBSD', '5']
print('PASS Darwin native nb6 and target nb5')
