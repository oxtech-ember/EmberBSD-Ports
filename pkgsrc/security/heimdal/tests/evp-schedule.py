#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Run ordinary EVP roundtrip and allocation-failure tests on Heimdal sources."""
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
tests = Path(__file__).resolve().parent
with tempfile.TemporaryDirectory() as tmp:
    directory = Path(tmp)
    for name in ('test.c', 'krb5_locl.h'):
        shutil.copyfile(tests / name, directory / name)
    shutil.copyfile(source / 'lib/krb5/crypto-evp.c', directory / 'crypto-evp.c')
    text = (source / 'lib/krb5/crypto.c').read_text()
    start = text.index('static krb5_error_code\n_key_schedule(')
    end = text.index('\n/********', start)
    (directory / 'key-schedule.inc').write_text(text[start:end] + '\n')
    for sanitize in (False, True):
        cmd = [str(args.cc.resolve(strict=True)), '-std=c11', '-g']
        if sanitize:
            cmd.append('-fsanitize=address,undefined')
        cmd += ['-I' + str(args.openssl_prefix / 'include'),
                '-L' + str(args.openssl_prefix / 'lib'),
                '-Wl,-rpath,' + str(args.openssl_prefix / 'lib'),
                str(directory / 'test.c'), '-lcrypto', '-o', str(directory / 'test')]
        subprocess.run(cmd, check=True)
        subprocess.run([str(directory / 'test')], check=True)
