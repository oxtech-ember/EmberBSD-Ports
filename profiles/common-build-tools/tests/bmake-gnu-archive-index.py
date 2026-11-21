#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""An archive with a GNU symbol table is fresh; an archive without an index is not.

llvm-ar writes ELF archives with the GNU symbol table "/" and no __.SYMDEF.
make must take that table as the index; else each archive is built again in
each pass, and a consumer can link while the archive is written again. An
archive without any index must still be built again. The check discriminates
only where bmake looks for __.SYMDEF, as on macOS.
"""

import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile

p = argparse.ArgumentParser()
for option in ('make', 'cc', 'ar', 'work'):
    p.add_argument('--' + option, required=True)
a = p.parse_args()
if sys.platform != 'darwin':
    # bmake reads no __.SYMDEF index on other hosts.
    print('SKIP: GNU archive index check needs macOS')
    sys.exit(0)

with tempfile.TemporaryDirectory(dir=a.work) as temp:
    root = Path(temp)
    (root / 'a.c').write_text('int a(void) { return 1; }\n')
    subprocess.run([a.cc, '-c', str(root / 'a.c'), '-o', str(root / 'a.o')], check=True)
    (root / 'Makefile').write_text('.SUFFIXES: .a\n.LIBS: .a\nlibsample.a: a.o\n\t' + a.ar +
                                   ' crsD --format=gnu $@ $>\n')

    def fresh():
        """Return whether make finds libsample.a up to date; make -q fails with 1 otherwise."""
        code = subprocess.run([a.make, '-r', '-q', '-f', 'Makefile', 'libsample.a'], cwd=root,
                              stdout=subprocess.DEVNULL).returncode
        assert code in (0, 1), f'make -q failed with {code}'
        return code == 0

    subprocess.run([a.make, '-r', '-f', 'Makefile', 'libsample.a'], cwd=root, check=True,
                   stdout=subprocess.DEVNULL)
    assert (root / 'libsample.a').read_bytes()[8:10] == b'/ ', 'no GNU symbol table'
    assert fresh(), 'archive with a GNU index is out of date'
    # A Darwin archive without an index has no symbol table: build it again.
    (root / 'libsample.a').unlink()
    subprocess.run([a.ar, 'qcS', '--format=darwin', str(root / 'libsample.a'), str(root / 'a.o')], check=True)
    os.utime(root / 'a.o', (1, 1))
    assert not fresh(), 'archive without an index is up to date'
print('PASS: GNU archive index')
