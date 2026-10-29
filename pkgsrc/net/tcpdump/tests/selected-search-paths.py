#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check the prepared tcpdump configure uses selected dependency paths."""
import argparse
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', required=True, type=Path)
parser.add_argument('--shell', required=True)
args = parser.parse_args()
recipe = Path(__file__).resolve().parents[1] / 'Makefile'
assert any(line.split('#', 1)[0].split() == ['USE_TOOLS+=', 'pkg-config']
           for line in recipe.read_text().splitlines())
configure = (args.source / 'configure').read_text()
macro = (args.source / 'aclocal.m4').read_text()
ac = (args.source / 'configure.ac').read_text()
for text in (configure, macro):
    assert 'LDFLAGS="$LDFLAGS -L/usr/local/lib"' not in text
    assert 'd="/usr/local/include/pcap"' not in text
    assert 'd="/usr/include/pcap"' not in text
for text in (configure, ac):
    assert 'LIBCRYPTO_CFLAGS="-I/usr/local/include"' not in text
    assert 'openssl_path=`$BREW --prefix openssl`' not in text
    assert 'libcrypto_root=$withval' in text
    assert 'requested libcrypto was not found' in text
options = (recipe.parent / 'options.mk').read_text()
assert 'CONFIGURE_ARGS+=\t--with-crypto' in options
assert 'CONFIGURE_ARGS+=\t--without-crypto' in options
start = configure.index('    if test "$GCC" = yes ; then')
end = configure.index('    case "$host_os" in', start)
block = configure[start:end].split('    else\n', 1)[1]
result = subprocess.run([args.shell, '-c',
    'V_INCLS=-I/selected/include; LDFLAGS=-L/selected/lib\n' + block +
    '\nprintf "%s\\n%s\\n" "$V_INCLS" "$LDFLAGS"'],
    check=True, capture_output=True, text=True)
assert result.stdout.splitlines() == ['-I/selected/include', '-L/selected/lib']
print('tcpdump selected dependency paths: PASS')
