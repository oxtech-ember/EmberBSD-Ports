#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Exercise rcsfreeze with selected tools and a spaced temporary directory."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser()
p.add_argument('--bin', required=True, type=Path)
p.add_argument('--shell', required=True, type=Path)
p.add_argument('--work-dir', required=True, type=Path)
a = p.parse_args()
bin_dir, shell = a.bin.resolve(strict=True), a.shell.resolve(strict=True)
with tempfile.TemporaryDirectory(prefix='rcs freeze ', dir=a.work_dir) as temporary:
    work = Path(temporary)
    (work / 'RCS').mkdir()
    (work / 'sample').write_text('hello\n')
    env = dict(os.environ, PATH=str(bin_dir) + os.pathsep + os.environ['PATH'], TMPDIR=str(work))
    subprocess.run([str(shell), str(bin_dir / 'ci'), '-q', '-t-test', '-u', 'sample'],
                   cwd=work, env=env, capture_output=True, check=True)
    subprocess.run([str(shell), str(bin_dir / 'rcsfreeze'), 'RELEASE'], input='release\n.\n',
                   cwd=work, env=env, capture_output=True, text=True, check=True)
    result = subprocess.run([str(bin_dir / 'rcs'), 'rlog', '-h', 'sample'],
                            cwd=work, env=env, capture_output=True, text=True, check=True)
    if 'RELEASE: 1.1' not in result.stdout:
        raise AssertionError('rcsfreeze did not assign the symbolic revision')
    if 'release' not in (work / 'RCS/.rcsfreeze.log').read_text():
        raise AssertionError('rcsfreeze did not record the log')
print('RCS freeze selected PATH and spaced TMPDIR: PASS')
