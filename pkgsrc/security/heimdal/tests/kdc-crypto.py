#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Check selected KDC HMAC and cipher paths with ordinary inputs."""
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('--kx509-source', required=True, type=Path)
parser.add_argument('--digest-source', required=True, type=Path)
parser.add_argument('--hcrypto-source', required=True, type=Path)
parser.add_argument('--cc', required=True, type=Path)
parser.add_argument('--openssl-prefix', required=True, type=Path)
parser.add_argument('--work', required=True, type=Path)
args = parser.parse_args()
work = args.work.resolve(strict=True)
cc = args.cc.resolve(strict=True)
prefix = args.openssl_prefix.resolve(strict=True)
with tempfile.TemporaryDirectory(dir=work) as tmp:
    dest = Path(tmp)
    shutil.copyfile(Path(__file__).with_suffix('.c'), dest / 'test.c')
    shutil.copyfile(Path(__file__).with_name('kdc-crypto-legacy.c'), dest / 'legacy.c')
    source = args.kx509_source.resolve(strict=True).read_text()
    start = source.index('static const unsigned char version_2_0')
    end = source.index('\n/*\n * Build a certifate', start)
    (dest / 'kx509.inc').write_text(source[start:end])
    start = source.index('#if defined(EMBERBSD_BASE_HEIMDAL)')
    end = source.index('\n#endif', start) + len('\n#endif')
    (dest / 'kx509-macros.inc').write_text(source[start:end] + '\n')
    source = args.digest_source.resolve(strict=True).read_text()
    start = source.index('static krb5_error_code\nntlm_unwrap_sessionkey')
    end = source.index('\n#define MS_CHAP_V2', start)
    (dest / 'digest.inc').write_text(source[start:end])
    subprocess.run([str(cc), '-std=c11', '-Wall', '-Wextra', '-Werror',
                    '-I' + str(dest), '-I' + str(args.hcrypto_source.resolve(strict=True) / 'lib'),
                    '-fsyntax-only', str(dest / 'legacy.c')], check=True)
    for sanitize in (False, True):
        cmd = [str(cc), '-std=c11', '-g']
        if sanitize:
            cmd.append('-fsanitize=address,undefined')
        cmd += ['-I' + str(prefix / 'include'), '-L' + str(prefix / 'lib'),
                '-Wl,-rpath,' + str(prefix / 'lib'), str(dest / 'test.c'),
                '-lcrypto', '-o', str(dest / 'test')]
        subprocess.run(cmd, check=True)
        subprocess.run([str(dest / 'test')], check=True)
