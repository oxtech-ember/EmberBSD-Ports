#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check actual pkgsrc native stage selection and reject invalid stage pairs."""
import argparse
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
for name in ('pkgsrc', 'makeconf', 'bmake', 'make_sys', 'stage_root', 'stage_prefix'):
    parser.add_argument(name)
a = parser.parse_args()
root = Path(a.pkgsrc)
toolbase = a.stage_root + a.stage_prefix
base = [a.bmake, '-m', a.make_sys, '-C', str(root / 'x11/libdisplay-info'),
        'MAKECONF=' + a.makeconf, 'TOOLBASE=' + toolbase,
        '-V', '${PKG_FAIL_REASON:U}']
cases = [
    ('selected', a.stage_root, a.stage_prefix, ''),
    ('relative prefix', a.stage_root, a.stage_prefix.lstrip('/'),
     'stage prefix must be absolute'),
    ('mismatched prefix', a.stage_root, '/elsewhere',
     'stage root and prefix must match TOOLBASE'),
    ('missing prefix', a.stage_root, '',
     'stage root and prefix must match TOOLBASE'),
]
for label, stage, prefix, expected in cases:
    result = subprocess.run(base + ['EMBERBSD_NATIVE_STAGE_ROOT=' + stage,
                            'EMBERBSD_NATIVE_STAGE_PREFIX=' + prefix],
                            check=True, text=True, capture_output=True)
    if (expected and expected not in result.stdout) or (not expected and result.stdout.strip()):
        raise SystemExit(f'{label}: unexpected result: {result.stdout}')
    print(f'{label}: PASS')
