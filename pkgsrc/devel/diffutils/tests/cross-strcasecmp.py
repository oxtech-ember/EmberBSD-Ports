#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Check that cross configure preserves gnulib's locale guesses."""
import argparse
from pathlib import Path
import re

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('source', type=Path, help='patched diffutils source')
args = parser.parse_args()
configure = (args.source / 'configure').read_text()
matches = re.findall(r'if test \$\{gl_cv_func_strcasecmp_works\+y\}.*?'
                     r'if test "\$cross_compiling" = yes\nthen :\n(.*?)\nelse case e in',
                     configure, re.S)
if len(matches) != 2 or any(branch.strip() != ':' for branch in matches):
    raise SystemExit('strcasecmp: cross branches do not preserve the upstream guess')
macro = (args.source / 'm4/strcasecmp.m4').read_text()
if not re.search(r'\[if test \$\? = 1; then.*?\],\s*\[:\]\)', macro, re.S):
    raise SystemExit('strcasecmp: autoconf input lacks an explicit cross branch')
print('PASS: upstream cross guesses retained; native runtime tests remain')
