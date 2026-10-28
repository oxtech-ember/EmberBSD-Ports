#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check the exported libfetch fix and affected package revisions."""
from pathlib import Path
import re
import os
import subprocess
import sys
import tempfile

if len(sys.argv) not in (3, 4) or (len(sys.argv) == 4 and sys.argv[3] != '--sanitize'):
    raise SystemExit('usage: libfetch-source.py EXPORTED_PKGSRC NATIVE_CLANG [--sanitize]')
root = Path(sys.argv[1])
compiler = Path(sys.argv[2]).resolve(strict=True)
ftp = (root / 'net/libfetch/files/ftp.c').read_text()
match = re.search(r"for \(i = 0; i < l && \*p; i\+\+, p\+\+\) \{\s*"
                 r"addr\[i\] = \(unsigned char\)strtol\(p, &p, 10\);\s*"
                 r"if \(\*p == '\\0' && i < l - 1\)\s*break;\s*\}", ftp)
assert match is not None
assert re.match(r'\s*if \(i < l\) \{\s*e = FTP_PROTOCOL_ERROR;\s*goto ouch;\s*\}',
                ftp[match.end():]) is not None
for package, revision in (('net/libfetch', 6), ('pkgtools/pkg_install', 9)):
    text = (root / package / 'Makefile').read_text()
    assert re.search(r'^PKGREVISION=\s*' + str(revision) + r'\s*$', text, re.MULTILINE)
assert 'FILESDIR.libfetch?=' in (root / 'pkgtools/pkg_install/Makefile').read_text()
# Compile the actual exported loop in a bounded local harness. Inputs below are
# complete valid records; no server or unpatched baseline is exercised.
loop = match.group(0)
program = r"""
#include <stdlib.h>
static int check(char *p, int l) {
    unsigned char addr[21] = {0};
    int i;
    LOOP
    if (i != l) return 1;
    for (i = 0; i < l; i++) if (addr[i] != 1) return 2;
    return 0;
}
int main(void) {
    char six[] = "1,1,1,1,1,1";
    char twentyone[] = "1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1";
    return check(six, 6) || check(twentyone, 21);
}
""".replace('LOOP', loop)
with tempfile.TemporaryDirectory(prefix='libfetch-source-') as temporary:
    source = Path(temporary) / 'test.c'
    binary = Path(temporary) / 'test'
    source.write_text(program)
    env = dict(os.environ, PATH=str(compiler.parent))
    flags = ['-fsanitize=address,undefined', '-fno-omit-frame-pointer'] if len(sys.argv) == 4 else []
    subprocess.run([str(compiler), '-Wall', '-Wextra', '-Werror', *flags, str(source),
                    '-o', str(binary)], env=env, check=True)
    subprocess.run([str(binary)], env=env, check=True)
print('PASS: exported guard, affected revisions, and valid bounded parser records')
