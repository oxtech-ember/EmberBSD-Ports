#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted check of real library symbol tables.
"""Reject an exported libc fallback in a built libedit object or library."""
import argparse
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--nm', required=True, type=Path)
parser.add_argument('artifacts', nargs='+', type=Path)
a = parser.parse_args()
for artifact in a.artifacts:
    done = subprocess.run([str(a.nm), '-g', str(artifact)], text=True,
                          capture_output=True, check=True, timeout=30)
    defined = set()
    for line in done.stdout.splitlines():
        fields = line.split()
        if len(fields) >= 2 and len(fields[-2]) == 1 and fields[-2].upper() != 'U':
            defined.add(fields[-1].removeprefix('_'))
    if 'el_init' not in defined:
        raise SystemExit(f'{artifact}: no public el_init; expected a compiled libedit artifact')
    if 'secure_getenv' in defined:
        raise SystemExit(f'{artifact}: secure_getenv fallback leaks into the public ABI')
print(f'PASS: private secure_getenv fallback in {len(a.artifacts)} compiled artifacts')
