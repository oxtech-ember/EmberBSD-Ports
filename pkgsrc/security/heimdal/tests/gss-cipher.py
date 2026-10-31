#!/usr/bin/env python3
"""Test GSS cipher context lifecycle with selected OpenSSL and hcrypto headers."""
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
cc = args.cc.resolve(strict=True)
prefix = args.openssl_prefix.resolve(strict=True)
here = Path(__file__).resolve().parent
text = (source / 'lib/gssapi/krb5/gsskrb5_locl.h').read_text()
start = text.index('typedef struct gsskrb5_cipher_ctx')
end = text.rindex('#endif')
helper = text[start:end]
with tempfile.TemporaryDirectory() as tmp:
    out = Path(tmp)
    (out / 'helper.inc').write_text('#define GSSKRB5_OPAQUE_CIPHER 1\n' + helper)
    (out / 'helper-legacy.inc').write_text(helper)
    arcfour = (source / 'lib/gssapi/krb5/arcfour.c').read_text()
    start = arcfour.index('OM_uint32\n_gssapi_get_mic_arcfour(')
    end = arcfour.index('\n\nOM_uint32\n_gssapi_verify_mic_arcfour(', start)
    (out / 'caller.inc').write_text(arcfour[start:end])
    start = arcfour.index('OM_uint32\n_gssapi_wrap_arcfour(')
    end = arcfour.index('\n\nOM_uint32 _gssapi_unwrap_arcfour(', start)
    (out / 'legacy-wrap.inc').write_text(arcfour[start:end])
    wrap = (source / 'lib/gssapi/krb5/wrap.c').read_text()
    start = wrap.index('static OM_uint32\nwrap_des\n')
    end = wrap.index('\n}\n', start) + 3
    (out / 'wrap-caller.inc').write_text(wrap[start:end])
    for file in ('gss-cipher.c', 'gss-cipher-legacy.c', 'gss-cipher-caller.c', 'gss-cipher-wrap.c', 'gss-legacy-wrap.c'):
        shutil.copyfile(here / file, out / file)
    subprocess.run([str(cc), '-std=c11', '-Wall', '-Wextra', '-Werror',
                    '-I' + str(source / 'lib'), '-I' + str(out),
                    '-fsyntax-only', str(out / 'gss-cipher-legacy.c')], check=True)
    for flags in ([], ['-fsanitize=address,undefined']):
        program = out / 'test'
        subprocess.run([str(cc), '-std=c11', *flags, '-I' + str(prefix / 'include'),
                        str(out / 'gss-cipher.c'), '-L' + str(prefix / 'lib'),
                        '-Wl,-rpath,' + str(prefix / 'lib'), '-lcrypto', '-o', str(program)], check=True)
        subprocess.run([str(program)], check=True)
        subprocess.run([str(cc), '-std=c11', *flags, '-I' + str(prefix / 'include'),
                        str(out / 'gss-cipher-caller.c'), '-L' + str(prefix / 'lib'),
                        '-Wl,-rpath,' + str(prefix / 'lib'), '-lcrypto', '-o', str(program)], check=True)
        subprocess.run([str(program)], check=True)
        subprocess.run([str(cc), '-std=c11', *flags, '-I' + str(prefix / 'include'),
                        str(out / 'gss-cipher-wrap.c'), '-L' + str(prefix / 'lib'),
                        '-Wl,-rpath,' + str(prefix / 'lib'), '-lcrypto', '-o', str(program)], check=True)
        subprocess.run([str(program)], check=True)
        subprocess.run([str(cc), '-std=c11', *flags, str(out / 'gss-legacy-wrap.c'), '-o', str(program)], check=True)
        subprocess.run([str(program)], check=True)
