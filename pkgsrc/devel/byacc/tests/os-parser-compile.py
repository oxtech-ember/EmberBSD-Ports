#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Generate and compile the upstream backtracking parser with strict warnings."""
import argparse
from pathlib import Path
import subprocess

p = argparse.ArgumentParser()
for option in ('source', 'yacc', 'cc', 'sysroot', 'work'):
    p.add_argument('--' + option, required=True, type=Path)
a = p.parse_args()
a.work.mkdir(parents=True, exist_ok=False)
grammar = (a.source / 'test/btyacc_calc1.y').resolve(strict=True)
subprocess.run([str(a.yacc), '-B', '-P', '-o', 'parser.c', str(grammar)],
               cwd=a.work, check=True)
subprocess.run([str(a.cc), '-isysroot', str(a.sysroot), '-Wall', '-Wextra', '-Werror',
                '-c', 'parser.c', '-o', 'parser.o'], cwd=a.work, check=True)
print('backtracking parser generation and compile: PASS')
