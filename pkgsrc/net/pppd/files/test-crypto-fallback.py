#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Run upstream crypto vectors with built-in digests on a Darwin build host."""
import argparse
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
for name in ('compiler', 'sysroot', 'crypto-prefix', 'source', 'build-config'):
    parser.add_argument('--' + name, type=Path, required=True)
args = parser.parse_args()
source = args.source / 'pppd'
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    stub = root / 'error.c'
    stub.write_text('void error(const char *fmt, ...) { (void)fmt; }\n')
    binary = root / 'crypto-test'
    command = [str(args.compiler), '-isysroot', str(args.sysroot),
               '-I' + str(args.crypto_prefix / 'include'),
               '-I' + str(args.build_config), '-I' + str(source),
               '-DUNIT_TEST', '-DPPP_WITH_OPENSSL', '-fsanitize=address,undefined',
               '-fno-omit-frame-pointer']
    command += [str(source / name) for name in
                ('crypto.c', 'ppp-md4.c', 'ppp-md5.c', 'ppp-sha1.c', 'ppp-des.c')]
    command += [str(stub), '-L' + str(args.crypto_prefix / 'lib'),
                '-Wl,-rpath,' + str(args.crypto_prefix / 'lib'), '-lcrypto',
                '-o', str(binary)]
    subprocess.run(command, check=True)
    subprocess.run([str(binary)], check=True)
print('PPP fallback crypto vectors with ASan/UBSan: PASS')
