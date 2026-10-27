#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Check the real pkgsrc Boost dependency graph and upstream b2 options."""
import argparse
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
for name in ('pkgsrc', 'bmake', 'makeconf', 'work'):
    parser.add_argument('--' + name, type=Path, required=True)
args = parser.parse_args()
assert all(getattr(args, n).is_absolute() for n in ('pkgsrc', 'bmake', 'makeconf', 'work'))
base = [str(args.bmake), '-C', str(args.pkgsrc / 'devel/boost-libs'),
        'EMBERBSD_DARWIN_BOOTSTRAP=yes', 'MAKECONF=' + str(args.makeconf),
        'WRKOBJDIR=' + str(args.work)]
for selected, enabled in ((None, True), ('icu', True), ('-icu', False)):
    common = base if selected is None else [*base, 'PKG_OPTIONS.boost-libs=' + selected]
    deps = subprocess.run([*common, 'show-depends'], check=True, capture_output=True, text=True).stdout
    flags = subprocess.run([*common, '-V', '${BJAM_ARGS}'], check=True, capture_output=True, text=True).stdout
    assert ('icu>=' in deps) == enabled
    assert ('--disable-icu' in flags) != enabled
    assert ('boost.locale.icu=off' in flags) != enabled
print('PASS: explicit Boost ICU dependency and b2 routing')
