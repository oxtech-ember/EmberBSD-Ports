#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Test the common Heimdal KDF against a known HMAC-SHA256 vector."""
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
    text = (source / 'lib/krb5/sp800-108-kdf.c').read_text()
    start = text.index('krb5_error_code\n_krb5_SP800_108_HMAC_KDF(')
    (directory / 'kdf.inc').write_text(text[start:])
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
