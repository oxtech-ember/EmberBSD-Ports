#!/usr/bin/env python3
"""Run the actual KDC DH ownership path with bounded failure injection."""
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile

p = argparse.ArgumentParser()
p.add_argument('--source', required=True, type=Path)
p.add_argument('--cc', required=True, type=Path)
p.add_argument('--openssl-prefix', required=True, type=Path)
a = p.parse_args()
source = a.source.resolve(strict=True)
with tempfile.TemporaryDirectory() as d:
    d = Path(d)
    shutil.copyfile(Path(__file__).with_suffix('.c'), d / 'test.c')
    text = (source / 'kdc/pkinit.c').read_text()
    start = text.index('static BIGNUM *\ninteger_to_BN(')
    end = text.index('\nkrb5_error_code\n_kdc_pk_rd_padata(', start)
    (d / 'pkinit.inc').write_text(text[start:end] + '\n')
    for sanitized in (False, True):
        cmd = [str(a.cc.resolve(strict=True)), '-std=c11', '-g']
        if sanitized:
            cmd.append('-fsanitize=address,undefined')
        cmd += ['-I' + str(a.openssl_prefix / 'include'),
                '-L' + str(a.openssl_prefix / 'lib'),
                '-Wl,-rpath,' + str(a.openssl_prefix / 'lib'),
                str(d / 'test.c'), '-lcrypto', '-o', str(d / 'test')]
        subprocess.run(cmd, check=True)
        subprocess.run([str(d / 'test')], check=True)
