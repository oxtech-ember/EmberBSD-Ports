#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise the real anchor certificate readers with a local test certificate."""
import argparse
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
for arg in ('source', 'cc', 'openssl', 'prefix', 'work'):
    p.add_argument('--' + arg, required=True, type=Path)
p.add_argument('--sanitize', action='store_true')
a = p.parse_args()
source = (a.source / 'smallapp/unbound-anchor.c').read_text()
start = source.index('#if !defined(HAVE_X509_GET_KEY_USAGE) ||')
end_marker = '#endif /* X509_NAME_GET_TEXT_BY_NID */'
end = source.index(end_marker, source.index(end_marker, start) + len(end_marker)) + len(end_marker)
functions = source[start:end]
with tempfile.TemporaryDirectory(dir=a.work) as temporary:
    root = Path(temporary)
    program = root / 'test.c'
    program.write_text('''#include <openssl/ssl.h>\n#include <openssl/x509v3.h>\n#include <stdint.h>\n#include <stdio.h>\n#include <string.h>\n''' + functions + '''\nint main(int argc, char **argv) {\n    FILE *f; X509 *cert; const X509_NAME *name; unsigned long usage;\n    if (argc != 2 || !(f = fopen(argv[1], "r"))) return 1;\n    cert = PEM_read_X509(f, NULL, NULL, NULL); fclose(f);\n    if (!cert) return 2;\n    name = X509_get_subject_name(cert);\n    usage = get_usage_of_ex(cert);\n    if (!has_valid_emailaddr(name, "test@example.org") ||\n        has_valid_emailaddr(name, "other@example.org") ||\n        (usage & 0x84) != 0x84) return 3;\n    print_name_ext(name, NID_commonName, "CN");\n    X509_free(cert); return 0;\n}\n''')
    cert, key, binary = root / 'cert.pem', root / 'key.pem', root / 'check'
    subprocess.run([str(a.openssl), 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
                    '-keyout', str(key), '-out', str(cert), '-days', '1',
                    '-subj', '/CN=EmberBSD test/emailAddress=test@example.org',
                    '-addext', 'keyUsage=digitalSignature,keyCertSign'],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run([str(a.openssl), 'verify', '-CAfile', str(cert), str(cert)],
                   check=True, stdout=subprocess.DEVNULL)
    flags = ['-fsanitize=address,undefined', '-fno-omit-frame-pointer'] if a.sanitize else []
    subprocess.run([str(a.cc), '-std=c11', '-Werror', '-Wall', *flags, '-I' + str(a.prefix / 'include'),
                    str(program), '-L' + str(a.prefix / 'lib'), '-lcrypto', '-o', str(binary)], check=True)
    subprocess.run([str(binary), str(cert)], check=True)
print('PASS: certificate subject and key usage readers')
