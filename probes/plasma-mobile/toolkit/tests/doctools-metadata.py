#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check native and cross DocTools consumers.
import os
from pathlib import Path
import subprocess
import sys

if len(sys.argv) != 4:
    raise SystemExit('Usage: doctools-metadata.py PKGSRC NATIVE_MAKECONF CROSS_MAKECONF')
root, native, cross = sys.argv[1:]
bmake = os.environ['BMAKE']
expected = 'kf6-kdoctools-generators-6.31.0{,nb[0-9]*}:../../devel/kf6-kdoctools-generators'
for config, cross_compile in ((native, 'no'), (cross, 'yes')):
    packages = ['audio/plasma6-plasma-pa', 'devel/kf6-kservice']
    if cross_compile == 'no':
        packages.insert(1, 'x11/plasma6-plasma-desktop')
    for package in packages:
        env = dict(os.environ, MAKECONF=config)
        result = subprocess.run([bmake, '-C', str(Path(root) / package),
                                 '_MAKEVARS_MK=defined', '_PKGSRC_BARRIER=yes',
                                 'USE_CROSS_COMPILE=' + cross_compile,
                                 '-V', '${TOOL_DEPENDS}'],
                                env=env, text=True, capture_output=True, check=True)
        if expected not in result.stdout.split():
            raise SystemExit(f'{package} cross={cross_compile}: {result.stdout!r}')
        print(f'{package} cross={cross_compile}: {expected}')
print('PASS: native and cross KDocTools generator versions')
