#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Check Darwin-only XZ and gettext-lib package metadata with bmake."""
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
    env = dict(os.environ, MAKECONF=str(makeconf.resolve(strict=True)))
    command = [str(args.bmake), '-C', str(pkgsrc / pkgpath),
               'MAKECONF=' + env['MAKECONF'], 'PKGSRCDIR=' + str(pkgsrc),
               'EMBERBSD_PKGSRCDIR=' + str(pkgsrc), 'show-vars',
               'VARNAMES=OPSYS PKGNAME PKGREVISION CONFIGURE_ARGS '
               'BUILD_MAKE_FLAGS INSTALL_MAKE_FLAGS SUBST_CLASSES '
               'SUBST_STAGE.darwin-libdir SUBST_FILES.darwin-libdir '
               'SUBST_SED.darwin-libdir']
    result = subprocess.run(command, env=env, check=True, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    values = result.stdout.splitlines()
    assert len(values) == 10, (pkgpath, result.stdout, result.stderr)
    return values

xz_native = query('archivers/xz', args.native_makeconf)
gettext_native = query('devel/gettext-lib', args.native_makeconf)
xz_target = query('archivers/xz', args.target_makeconf)
gettext_target = query('devel/gettext-lib', args.target_makeconf)

assert xz_native[:3] == ['Darwin', 'xz-5.8.4nb2', '2'], xz_native
assert gettext_native[:3] == ['Darwin', 'gettext-lib-1.0nb3', '3'], gettext_native
assert '--enable-relocatable' in gettext_native[3].split(), gettext_native
assert 'localedir=/usr/pkg/share/locale' in gettext_native[4].split(), gettext_native
assert 'prefix=/usr/pkg' not in gettext_native[4].split(), gettext_native
assert 'localedir=/usr/pkg/share/locale' not in gettext_native[5].split(), gettext_native
assert 'darwin-libdir' in gettext_native[6].split(), gettext_native
assert gettext_native[7] == 'pre-configure', gettext_native
assert gettext_native[8] == 'gettext-runtime/intl/Makefile.in', gettext_native
assert '/usr/pkg/lib' in gettext_native[9], gettext_native
assert 'darwin-libdir' not in gettext_target[6].split(), gettext_target
assert xz_target[:3] == ['NetBSD', 'xz-5.8.4nb2', '2'], xz_target
assert gettext_target[:3] == ['NetBSD', 'gettext-lib-1.0nb3', '3'], gettext_target
assert '--enable-relocatable' not in gettext_target[3].split(), gettext_target
assert 'prefix=/usr/pkg' not in gettext_target[4].split(), gettext_target
print('PASS: Darwin native revisions are isolated; NetBSD names and gettext options stay unchanged')
