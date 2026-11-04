#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check the actual package Makefile's incremental header dependencies."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('--bmake', required=True)
args = parser.parse_args()
makefile = Path(__file__).resolve().parents[3] / 'pkgsrc/devel/zlib/files/Makefile'
names = 'adler32 compress crc32 deflate gzclose gzlib gzread gzwrite infback inffast inflate inftrees trees uncompr zutil'.split()
headers = 'zlib.h zconf.h zutil.h crc32.h deflate.h trees.h gzguts.h inftrees.h inflate.h inffast.h inffixed.h'.split()
with tempfile.TemporaryDirectory(prefix='zlib-headers-') as directory:
    root = Path(directory)
    (root / 'Makefile').write_bytes(makefile.read_bytes())
    for name in names:
        (root / (name + '.c')).touch()
        (root / (name + '.lo')).touch()
    for name in headers:
        (root / name).touch()
    (root / 'libz.la').touch()
    for path in root.iterdir():
        os.utime(path, (1000000000, 1000000000))
    for name in names:
        os.utime(root / (name + '.lo'), (1000000100, 1000000100))
    os.utime(root / 'libz.la', (1000000200, 1000000200))
    def planned():
        result = subprocess.run([args.bmake, '-r', '-n', 'LIBTOOL=echo', 'CC=echo', 'PREFIX=/target', 'libz.la'], cwd=root, text=True, capture_output=True)
        assert result.returncode == 0, result.stderr
        return {name for name in names if ('-o ' + name + '.lo ') in result.stdout}
    assert planned() == set()
    os.utime(root / 'zconf.h', (1000000300, 1000000300))
    assert planned() == set(names)
    os.utime(root / 'zconf.h', (1000000000, 1000000000))
    os.utime(root / 'gzguts.h', (1000000300, 1000000300))
    assert planned() == {'gzclose', 'gzlib', 'gzread', 'gzwrite', 'zutil'}
    os.utime(root / 'gzguts.h', (1000000000, 1000000000))
    os.utime(root / 'inffixed.h', (1000000300, 1000000300))
    assert planned() == {'inftrees'}
print('zlib incremental header dependencies PASS')
