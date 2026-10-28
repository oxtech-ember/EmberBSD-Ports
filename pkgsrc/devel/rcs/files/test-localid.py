#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Check configured RCS local keyword using ordinary revision operations."""
import argparse
from pathlib import Path
import re
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('--bin', type=Path, required=True)
parser.add_argument('--shell', type=Path, required=True)
parser.add_argument('--work-dir', type=Path, required=True)
parser.add_argument('--keyword', required=True)
args = parser.parse_args()
if not re.fullmatch(r'[A-Za-z]{1,32}', args.keyword):
    parser.error('keyword must contain 1-32 ASCII letters')
bin_dir = args.bin.resolve(strict=True)
shell = args.shell.resolve(strict=True)
with tempfile.TemporaryDirectory(dir=args.work_dir) as temporary:
    work = Path(temporary)
    first, second = work / 'first', work / 'second'
    for directory in (first, second):
        (directory / 'RCS').mkdir(parents=True)
    source = first / 'sample'
    source.write_text(f'${args.keyword}$\n', encoding='ascii')
    def run(directory, name, *words):
        return subprocess.run([str(shell), str(bin_dir / name), *words],
                              cwd=directory, check=True, capture_output=True, text=True)
    run(first, 'ci', '-q', '-t-test', '-u', 'sample')
    result = source.read_text(encoding='ascii')
    if not re.fullmatch(r'\$' + re.escape(args.keyword) + r': sample,v 1\.1 [^\n]+ Exp \$\n', result):
        raise AssertionError('local keyword did not expand as Id')
    (second / 'sample').write_text(result, encoding='ascii')
    run(second, 'ci', '-q', '-k', '-t-test', '-u', 'sample')
    run(second, 'rcsdiff', '-q', 'sample')
    if (second / 'sample').read_text(encoding='ascii') != result:
        raise AssertionError('ci -k changed the expanded keyword')
print('RCS local keyword expansion, ci -k and comparison: PASS')
