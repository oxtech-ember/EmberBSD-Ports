#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Check GSS NTLM valid operations and failure state with selected tools."""
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('--source', required=True, type=Path)
parser.add_argument('--cc', required=True, type=Path)
parser.add_argument('--openssl-prefix', required=True, type=Path)
parser.add_argument('--work', required=True, type=Path)
args = parser.parse_args()
source = args.source.resolve(strict=True)
cc = args.cc.resolve(strict=True)
prefix = args.openssl_prefix.resolve(strict=True)
with tempfile.TemporaryDirectory(dir=args.work.resolve(strict=True)) as tmp:
    dest = Path(tmp)
    for src, target in (('gss-ntlm-hmac.c', 'test.c'), ('gss-ntlm-hmac-legacy.c', 'legacy.c')):
        shutil.copyfile(Path(__file__).with_name(src), dest / target)
    text = (source / 'lib/gssapi/ntlm/crypto.c').read_text()
    start = text.index('static void\nencode_le_uint32(')
    end = text.index('\n\nstatic void\ndecode_le_uint32', start)
    encode = text[start:end]
    start = text.index('static OM_uint32\nv2_sign_message(')
    end = text.index('\n/*\n *\n */\n\n#define CTX_FLAGS_ISSET', start)
    (dest / 'functions.inc').write_text(encode + '\n' + text[start:end] + '\n')
    start = text.index('OM_uint32 GSSAPI_CALLCONV\n_gss_ntlm_get_mic')
    end = text.index('\n/*\n *\n */', start)
    (dest / 'get-mic.inc').write_text(text[start:end] + '\n')
    subprocess.run([str(cc), '-std=c11', '-Wall', '-Wextra',
                    '-Werror=incompatible-pointer-types', '-Werror=return-type',
                    '-I' + str(dest), '-I' + str(source / 'lib'),
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
