#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Test actual exported shell-wrapper phase scanner and option operands."""
from pathlib import Path
import subprocess
import sys

if len(sys.argv) != 3:
    raise SystemExit('usage: shell-wrapper-scan.py SELECTED_SHELL EXPORTED_SCAN')
shell, scan = map(Path, sys.argv[1:])
if not all(p.is_absolute() and p.is_file() for p in (shell, scan)):
    raise SystemExit('select absolute existing shell and scanner')
cases = [
    (['-c'], 'no'), (['-E'], 'no'), (['-S'], 'no'),
    (['-fsyntax-only'], 'no'), (['-M'], 'no'), (['-MM'], 'no'),
    (['-MD'], 'yes'), (['-MMD'], 'yes'),
    (['-o', '-c'], 'yes'), (['-I', '-S'], 'yes'),
    (['-Xlinker', '-S'], 'yes'), (['-Xclang', '-fsyntax-only'], 'yes'),
    (['-l', '-c'], 'yes'), (['-arch', '-S'], 'yes'),
    (['--', '-c'], 'yes'), (['-o', '--', '-c'], 'no'),
    (['-c', '--', '-E'], 'no'), (['-unknown', '-c'], 'no'),
]
for args, expected in cases:
    result = subprocess.run([str(shell), '-c', 'append_link_args=yes; . "$1"; printf "%s" "$append_link_args"', 'scan-test', str(scan), *args], text=True, capture_output=True)
    if result.returncode or result.stdout != expected:
        raise ValueError(f'{args}: expected {expected}, got {result.stdout!r}, {result.stderr!r}')
print('PASS: phase flags, option operands, forwarded options and -- boundary')
