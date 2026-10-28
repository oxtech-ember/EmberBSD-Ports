#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Check normal and invalid modes using the selected checkperms executable."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser()
p.add_argument('--checkperms', required=True)
args = p.parse_args()
if not os.path.isabs(args.checkperms) or not os.access(args.checkperms, os.X_OK):
    p.error('select an executable by absolute path')
with tempfile.TemporaryDirectory(prefix='checkperms-test-', dir=os.environ.get('TMPDIR')) as work:
    path = Path(work) / 'file'
    path.write_text('test\n')
    path.chmod(0o644)
    result = subprocess.run([args.checkperms, '-e'], input=str(path) + '\n', text=True, capture_output=True)
    if result.returncode:
        raise SystemExit('ordinary permissions rejected: ' + result.stderr)
    path.chmod(0o002)
    result = subprocess.run([args.checkperms, '-e'], input=str(path) + '\n', text=True, capture_output=True)
    if result.returncode == 0 or 'world-writable file' not in result.stdout + result.stderr:
        raise SystemExit('world-writable permissions were not rejected: ' + result.stderr)
print('PASS: selected checkperms accepts ordinary and rejects world-writable modes')
