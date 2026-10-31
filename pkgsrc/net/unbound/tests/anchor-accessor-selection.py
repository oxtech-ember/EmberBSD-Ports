#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check accessor selection on OpenSSL and LibreSSL compatibility macros."""
import argparse
from pathlib import Path
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--source', type=Path, required=True)
p.add_argument('--cc', type=Path, required=True)
a = p.parse_args()
text = (a.source / 'smallapp/unbound-anchor.c').read_text()
start = text.index('#if !defined(HAVE_X509_GET_KEY_USAGE) ||')
marker = '#endif /* X509_NAME_GET_TEXT_BY_NID */'
end = text.index(marker, text.index(marker, start) + len(marker)) + len(marker)
fragment = text[start:end]
for name, definitions, new_length, get0 in (
    ('OpenSSL 4.1', ['OPENSSL_VERSION_NUMBER=0x40100000L'], True, True),
    ('OpenSSL 3', ['OPENSSL_VERSION_NUMBER=0x30000000L'], False, True),
    ('LibreSSL without capability', ['OPENSSL_VERSION_NUMBER=0x40100000L', 'LIBRESSL_VERSION_NUMBER=0x4000000fL'], False, False),
    ('LibreSSL with capability', ['OPENSSL_VERSION_NUMBER=0x40100000L', 'LIBRESSL_VERSION_NUMBER=0x4000000fL', 'HAVE_ASN1_STRING_GET0_DATA=1'], False, True),
):
    result = subprocess.run([str(a.cc), '-E', '-P', '-x', 'c', *['-D' + v for v in definitions], '-'],
                            input=fragment, capture_output=True, text=True, check=True).stdout
    assert ('return ASN1_STRING_get_length(s)' in result) == new_length, name
    assert ('ASN1_STRING_get0_data(' in result) == get0, name
    assert ('ASN1_STRING_data(' in result) != get0, name
print('PASS: OpenSSL and LibreSSL accessor selection')
