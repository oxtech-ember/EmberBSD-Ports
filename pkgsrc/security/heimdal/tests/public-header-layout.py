#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Compile the public krb5 header in Heimdal's package include layouts."""

import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', required=True, type=Path,
                    help='patched Heimdal source root')
parser.add_argument('--headers', required=True, type=Path,
                    help='installed Heimdal include/krb5 directory')
parser.add_argument('--cc', required=True, type=Path,
                    help='selected C compiler')
parser.add_argument('--cflag', action='append', default=[],
                    help='compiler argument; may be repeated')
args = parser.parse_args()

source = args.source.resolve(strict=True)
headers = args.headers.resolve(strict=True)
cc = args.cc.resolve(strict=True)
public = source / 'lib/krb5/krb5.h'
if not public.is_file():
    parser.error(f'missing public header: {public}')

with tempfile.TemporaryDirectory() as tmp:
    include = Path(tmp) / 'include'
    krb5 = include / 'krb5'
    krb5.mkdir(parents=True)
    for header in headers.glob('*.h'):
        shutil.copyfile(header, krb5 / header.name)
    shutil.copyfile(public, krb5 / 'krb5.h')

    source_file = Path(tmp) / 'public-header.c'
    source_file.write_text(
        '#include <krb5.h>\n'
        'int main(void) { krb5_context context = 0; return context != 0; }\n'
    )
    subprocess.run([str(cc), *args.cflag, '-fsyntax-only', '-I' + str(krb5),
                    str(source_file)], check=True)

    source_file.write_text(
        '#include <krb5/krb5.h>\n'
        'int main(void) { krb5_context context = 0; return context != 0; }\n'
    )
    subprocess.run([str(cc), *args.cflag, '-fsyntax-only', '-I' + str(include),
                    str(source_file)], check=True)

print('PASS: public krb5 header resolves its package-layout siblings')
