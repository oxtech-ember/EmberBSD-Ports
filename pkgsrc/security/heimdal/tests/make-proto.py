#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Check make-proto.pl filters static functions in preprocessor branches."""
import argparse
from pathlib import Path
import re
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', required=True, type=Path,
                    help='patched Heimdal source root')
parser.add_argument('--perl', required=True, type=Path,
                    help='selected native Perl interpreter')
args = parser.parse_args()
script = args.source.resolve(strict=True) / 'cf/make-proto.pl'
perl = args.perl.resolve(strict=True)
if not script.is_file():
    parser.error(f'missing prototype generator: {script}')

fixture = "\n".join((
    'static int', 'preceding_private(void)', '{', '    return 0;', '}',
    '#if OPENSSL_VERSION_NUMBER >= 0x10100000UL', 'static int',
    'match_keys_rsa(int value)', '{', '    return value;', '}', '#else',
    'static int', 'match_keys_rsa(int value)', '{', '    return value + 1;',
    '}', '#endif', 'int', 'hx509_public_after_branch(int value)', '{',
    '    return match_keys_rsa(value);', '}', ''))
with tempfile.TemporaryDirectory(prefix='heimdal-make-proto-') as tmp:
    work = Path(tmp)
    source = work / 'fixture.c'
    output = work / 'fixture-protos.h'
    source.write_text(fixture)
    subprocess.run([str(perl), str(script), '-q', '-P', 'comment', '-o',
                    str(output), str(source)], check=True)
    generated = output.read_text()
    if re.search(r'\bmatch_keys_rsa\b', generated):
        raise SystemExit('conditional static match_keys_rsa leaked into prototypes')
    if 'hx509_public_after_branch (int /*value*/);' not in generated:
        raise SystemExit('public prototype after conditional branch was lost')

print('PASS: conditional static functions are filtered; public prototype retained')
