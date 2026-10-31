#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Test the common Heimdal KAFS KDF against a known vector."""
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
with tempfile.TemporaryDirectory() as tmp:
    directory = Path(tmp)
    shutil.copyfile(Path(__file__).with_suffix('.c'), directory / 'test.c')
    text = (args.source.resolve(strict=True) / 'lib/kafs/rxkad_kdf.c').read_text()
    start = text.index('static int\nrxkad_derive_des_key(')
    end = text.index('\n/**', start)
    (directory / 'kafs.inc').write_text(text[start:end] + '\n')
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
