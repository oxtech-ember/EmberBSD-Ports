#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Test real PKINIT DH group selection with the selected native OpenSSL."""
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('--source', required=True, type=Path)
parser.add_argument('--cc', required=True, type=Path)
parser.add_argument('--openssl-prefix', required=True, type=Path)
args = parser.parse_args()
source = args.source.resolve(strict=True)
with tempfile.TemporaryDirectory() as tmp:
    directory = Path(tmp)
    shutil.copyfile(Path(__file__).with_suffix('.c'), directory / 'test.c')
    text = (source / 'lib/krb5/pkinit.c').read_text()
    start = text.index('static BIGNUM *\ninteger_to_BN(')
    end = text.index('\nstruct certfind', start)
    (directory / 'pkinit.inc').write_text(text[start:end] + '\n')
    for sanitize in (False, True):
        cmd = [str(args.cc.resolve(strict=True)), '-std=c11', '-g', '-Wno-deprecated-declarations']
        if sanitize:
            cmd.append('-fsanitize=address,undefined')
        cmd += ['-I' + str(args.openssl_prefix / 'include'),
                '-L' + str(args.openssl_prefix / 'lib'),
                '-Wl,-rpath,' + str(args.openssl_prefix / 'lib'),
                str(directory / 'test.c'), '-lcrypto', '-o', str(directory / 'test')]
        subprocess.run(cmd, check=True)
        subprocess.run([str(directory / 'test')], check=True)
