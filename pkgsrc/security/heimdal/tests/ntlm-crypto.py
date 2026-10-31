#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Check valid NTLM primitives and error propagation using the selected OpenSSL."""
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
    text = (args.source.resolve(strict=True) / 'lib/ntlm/ntlm.c').read_text()
    chunks = []
    for name in ('heim_ntlm_keyex_wrap', 'heim_ntlm_keyex_unwrap', 'heim_ntlm_derive_ntlm2_sess', 'heim_ntlm_ntlmv2_key', 'heim_ntlm_calculate_lm2'):
        start = text.index('\nint\n' + name + '(') + 1
        brace = text.index('{', start)
        depth = 0
        for i in range(brace, len(text)):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0:
                    chunks.append(text[start:i+1])
                    break
        else:
            raise ValueError('unterminated function ' + name)
    (directory / 'functions.inc').write_text('\n\n'.join(chunks) + '\n')
    start = text.index('#if defined(EMBERBSD_BASE_HEIMDAL)')
    end = text.index('\n#endif', start) + len('\n#endif')
    (directory / 'ntlm-macros.inc').write_text(text[start:end] + '\n')
    legacy = Path(__file__).with_name('ntlm-legacy-hmac.c')
    subprocess.run([str(args.cc.resolve(strict=True)), '-std=c11', '-Wall', '-Wextra',
                    '-Werror', '-I' + str(directory),
                    '-I' + str(args.source.resolve(strict=True) / 'lib'),
                    '-fsyntax-only', str(legacy)], check=True)
    for sanitize in (False, True):
        cmd = [str(args.cc.resolve(strict=True)), '-std=c11', '-g']
        if sanitize:
            cmd.append('-fsanitize=address,undefined')
        cmd += ['-I' + str(args.openssl_prefix / 'include'), '-L' + str(args.openssl_prefix / 'lib'),
                '-Wl,-rpath,' + str(args.openssl_prefix / 'lib'),
                str(directory / 'test.c'), '-lcrypto', '-o', str(directory / 'test')]
        subprocess.run(cmd, check=True)
        subprocess.run([str(directory / 'test')], check=True)
