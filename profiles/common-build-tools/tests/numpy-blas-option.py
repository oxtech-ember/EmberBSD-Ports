#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Check the numpy blas option with the real pkgsrc graph.

With the option (the default), numpy depends on a BLAS package and needs
Fortran. Without it, numpy builds its lapack_lite fallback. A numpy user
gets BLAS only when the numpy that it builds against has the option: the
options of an installed numpy package, else the options of the recipe.
"""
import argparse
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
for name in ('pkgsrc', 'bmake', 'makeconf', 'work'):
    parser.add_argument('--' + name, type=Path, required=True)
args = parser.parse_args()
assert all(getattr(args, n).is_absolute() for n in ('pkgsrc', 'bmake', 'makeconf', 'work'))
BLAS = ('math/lapack', 'math/blas', 'math/cblas', 'math/openblas')
BLAS_TREE = ('lapack', 'blas', 'cblas', 'openblas')


def query(pkgpath, option, *arguments):
    # pkg-build-options.mk asks a child make for numpy's options. A command
    # line assignment does not reach that child, so select it in MAKECONF.
    args.work.mkdir(parents=True, exist_ok=True)
    name = 'default' if option is None else option
    makeconf = args.work / ('mk-' + name + '.conf')
    select = ('.undef PKG_OPTIONS.py-numpy' if option is None
              else 'PKG_OPTIONS.py-numpy= ' + option)
    makeconf.write_text('.include "%s"\n%s\n' % (args.makeconf, select))
    command = [str(args.bmake), '-C', str(args.pkgsrc / pkgpath),
               'MAKECONF=' + str(makeconf), 'WRKOBJDIR=' + str(args.work)]
    return subprocess.run([*command, *arguments], check=True,
                          capture_output=True, text=True).stdout


for option, enabled in ((None, True), ('blas', True), ('-blas', False)):
    languages = query('math/py-numpy', option, '-V', '${USE_LANGUAGES}').split()
    wheel = query('math/py-numpy', option, '-V', '${WHEEL_ARGS}')
    depends = query('math/py-numpy', option, '-V', '${DEPENDS} ${BUILD_DEPENDS}')
    assert ('fortran' in languages) == enabled, (option, languages)
    assert ('-Dallow-noblas=true' in wheel) != enabled, (option, wheel)
    assert ('-Dblas=none' in wheel) != enabled, (option, wheel)
    assert any(p in depends for p in BLAS) == enabled, (option, depends)
    # A cv2 user follows numpy's build options through its buildlink3.mk.
    # BLAS is an indirect dependency there, so it is only in the tree.
    user = 'graphics/opencv-contrib'
    tree = query(user, option, '-V', '${BUILDLINK_TREE}').split()
    used = query(user, option, '-V', '${PKG_BUILD_OPTIONS.${PYPKGPREFIX}-numpy}').split()
    assert any(p in tree for p in BLAS_TREE) == ('blas' in used), (option, used, tree)
    pkg_info = query(user, option, '-V', '${PKG_INFO}').split()
    numpy = query(user, option, '-V', '${PYPKGPREFIX}-numpy').strip()
    installed = subprocess.run([*pkg_info, '-Q', 'PKG_OPTIONS', numpy],
                               capture_output=True, text=True)
    if installed.returncode == 0:
        # The installed package decides, whatever the current MAKECONF says.
        assert used == installed.stdout.split(), (option, used, installed.stdout)
    else:
        assert ('blas' in used) == enabled, (option, used)
print('PASS: numpy blas option selects BLAS and Fortran together')
