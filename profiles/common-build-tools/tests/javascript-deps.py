#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check real bmake mapping from JS names to package dependencies."""
import argparse
import os
from pathlib import Path
import subprocess

p = argparse.ArgumentParser(description=__doc__)
for name in ('pkgsrc', 'bmake', 'makeconf'):
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
env = dict(os.environ, MAKECONF=str(a.makeconf))
base = [str(a.bmake), 'EMBERBSD_DARWIN_BOOTSTRAP=yes',
        'JS_MODULE_DEPENDS=foo=node-foo>=1:../../devel/node-foo @scope/bar=node-bar>=2:../../devel/node-bar']
def run(*args):
    return subprocess.run([*base, *args], cwd=a.pkgsrc / 'devel/node-isexe', env=env,
                          text=True, capture_output=True, check=True).stdout
result = run('-V', '${DEPENDS}')
assert 'node-foo>=1:../../devel/node-foo' in result and 'node-bar>=2:../../devel/node-bar' in result
command = run('-n', 'do-build')
assert '--dependency foo' in command and '--dependency @scope/bar' in command
print('common JS dependency to pkgsrc mapping PASS')
