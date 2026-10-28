#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check pkg_install's exported configure helper and required build tools."""
from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: pkg-install-configure.py EXPORTED_PKGSRC')
root = Path(sys.argv[1]) / 'pkgtools/pkg_install'
recipe = (root / 'Makefile').read_text()
configure = (root / 'files/configure').read_text()
assert re.search(r'^PKGREVISION=\s*10\s*$', recipe, re.M)
assert re.search(r'^USE_TOOLS\+=\s*pkg-config nm\s*$', recipe, re.M)
assert configure.count('ac_fn_c_try_link ()') == 1
assert configure.index('ac_fn_c_try_link ()') < configure.index('checking for __db185_open in -ldb')
print('PASS: pkg_install declares configure tools and defines the link helper before its probe')
