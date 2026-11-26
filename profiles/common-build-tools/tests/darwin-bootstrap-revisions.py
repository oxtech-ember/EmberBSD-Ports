#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Check Darwin-only bootstrap package revisions and nbsed feature ordering."""
import argparse
import os
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
for name in ('pkgsrc', 'native-makeconf', 'target-makeconf', 'bmake'):
    parser.add_argument('--' + name, type=Path, required=True)
args = parser.parse_args()
pkgsrc = args.pkgsrc.resolve(strict=True)

def query(pkgpath, makeconf):
    makeconf = makeconf.resolve(strict=True)
    env = dict(os.environ, MAKECONF=str(makeconf))
    command = [str(args.bmake), '-C', str(pkgsrc / pkgpath),
               'MAKECONF=' + str(makeconf), 'PKGSRCDIR=' + str(pkgsrc),
               'EMBERBSD_PKGSRCDIR=' + str(pkgsrc), 'show-vars',
               'VARNAMES=OPSYS PKGNAME PKGREVISION MISSING_FEATURES BUILDLINK_TREE']
    result = subprocess.run(command, env=env, check=True, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    values = result.stdout.splitlines()
    assert len(values) == 5, (pkgpath, result.stdout, result.stderr)
    return values

mksh_native = query('shells/mksh', args.native_makeconf)
nbsed_native = query('textproc/nbsed', args.native_makeconf)
mksh_target = query('shells/mksh', args.target_makeconf)
nbsed_target = query('textproc/nbsed', args.target_makeconf)

assert mksh_native[:3] == ['Darwin', 'mksh-59cnb4', '4'], mksh_native
assert nbsed_native[:3] == ['Darwin', 'nbsed-20240312nb3', '3'], nbsed_native
assert nbsed_native[3].split() == ['nbcompat'], nbsed_native
assert 'libnbcompat' in nbsed_native[4].split(), nbsed_native
assert mksh_target[:3] == ['NetBSD', 'mksh-59cnb3', '3'], mksh_target
assert nbsed_target[:3] == ['NetBSD', 'nbsed-20240312nb2', '2'], nbsed_target
assert nbsed_target[3].split() == ['nbcompat'], nbsed_target
assert 'libnbcompat' in nbsed_target[4].split(), nbsed_target
print('PASS: Darwin bootstrap revisions are isolated; nbsed selects libnbcompat before prefs evaluation')
