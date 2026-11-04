#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check every base libz source using an actual OS compiler command."""
import argparse
from pathlib import Path
import shlex
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--command-file', required=True, type=Path)
parser.add_argument('--zlib-source', required=True, type=Path)
args = parser.parse_args()
words = shlex.split(args.command_file.read_text())
assert '-Wwrite-strings' in words and '-Wcast-qual' in words and '-Werror' in words
source_index = next(i for i, word in enumerate(words) if Path(word).name == 'inflate.c')
old = str(Path(words[source_index]).parent)
assert words.count('-o') == 1 and words.count('-c') == 1
out = words.index('-o')
assert out + 1 < len(words)
words[out:out + 2] = []
words.remove('-c')
words = [word.replace(old, str(args.zlib_source)) for word in words]
source_index = next(i for i, word in enumerate(words) if word.endswith('/inflate.c'))
words.append('-fsyntax-only')
for name in ('adler32.c', 'compress.c', 'crc32.c', 'deflate.c', 'infback.c',
             'inffast.c', 'inflate.c', 'inftrees.c', 'trees.c', 'uncompr.c',
             'zutil.c', 'gzwrite.c', 'gzlib.c', 'gzread.c', 'gzclose.c'):
    words[source_index] = str(args.zlib_source / name)
    subprocess.run(words, check=True)
print('15 OS libz sources with actual compiler flags PASS')
