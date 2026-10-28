#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Check two ordinary rcsdiff labels against a working file."""
import argparse
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser()
p.add_argument('--bin', required=True, type=Path)
p.add_argument('--shell', required=True, type=Path)
p.add_argument('--work-dir', required=True, type=Path)
a = p.parse_args()
bin_dir, shell = a.bin.resolve(strict=True), a.shell.resolve(strict=True)
with tempfile.TemporaryDirectory(dir=a.work_dir) as temporary:
    work = Path(temporary)
    (work / 'RCS').mkdir()
    source = work / 'sample'
    source.write_text('first\n')
    subprocess.run([str(shell), str(bin_dir / 'ci'), '-q', '-t-test', '-u', 'sample'],
                   cwd=work, capture_output=True, check=True)
    source.chmod(0o644)
    source.write_text('second\n')
    result = subprocess.run([str(shell), str(bin_dir / 'rcsdiff'), '-u',
                             '-L', 'old-label', '-L', 'new-label', 'sample'],
                            cwd=work, capture_output=True, text=True)
    if result.returncode != 1 or '--- old-label\n' not in result.stdout or '+++ new-label\n' not in result.stdout:
        raise AssertionError('two labels did not produce the expected diff')
print('RCS two diff labels: PASS')
