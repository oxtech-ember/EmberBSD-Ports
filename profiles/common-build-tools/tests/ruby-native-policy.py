#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Check selected pkgsrc metadata for native Ruby and target policy."""
import argparse
import os
import subprocess
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
for name in ('pkgsrc', 'makeconf', 'bmake'):
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
env = dict(os.environ, MAKECONF=str(a.makeconf))

def query(mode, *extra):
    result = subprocess.run([str(a.bmake), '-C', str(a.pkgsrc / 'lang/ruby40'),
                             'USE_CROSS_COMPILE=' + mode, *extra, 'show-vars',
                             'VARNAMES=OPSYS PKG_OPTIONS CONFIGURE_ARGS LDFLAGS'],
                            env=env, check=True, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    values = result.stdout.splitlines()
    assert len(values) == 4, values
    return values

native = query('no')
assert native[0] == 'Darwin' and 'ruby-build-ri-db' not in native[1].split(), native
assert 'ruby-yjit' in native[1].split() and '--enable-install-doc=no' in native[2], native
assert '--enable-load-relative' in native[2] and '--with-destdir=' in native[2], native
assert native[3].split().count('-Wl,-headerpad_max_install_names') == 1, native
explicit = query('no', 'PKG_OPTIONS.ruby=ruby-build-ri-db')
assert 'ruby-build-ri-db' in explicit[1].split() and '--enable-install-doc=no' not in explicit[2], explicit
target = query('yes')
assert target[0] == 'NetBSD' and '--enable-load-relative' not in target[2], target
assert '-Wl,-headerpad_max_install_names' not in target[3].split(), target
print('PASS native defaults, explicit RI selection and target isolation')
