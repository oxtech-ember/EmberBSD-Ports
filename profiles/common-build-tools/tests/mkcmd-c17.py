#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted mkcmd GCC 16 build regression.
"""Compile the patched mkcmd 8.14 sources with the recipe's C dialect.

mkcmd uses unprototyped () declarations, which C23 removed, and main.c
called Cleanup() without a declaration. Read the wrapper flags of the
exported recipe with real bmake, then compile every bin/mkcmd C file of a
patched work source (make patch) with the selected GCC.
"""
import argparse
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--bmake', required=True, type=Path)
parser.add_argument('--pkgsrc', required=True, type=Path, help='an exported pkgsrc tree')
parser.add_argument('--wrksrc', required=True, type=Path,
                    help='mkcmd-8.14 after make patch of that recipe')
parser.add_argument('--cc', required=True, type=Path, help='the GCC 16 C compiler')
parser.add_argument('--work-parent', required=True, type=Path)
a = parser.parse_args()

environment = {'PATH': os.environ.get('PATH', '/usr/bin:/bin'),
               'HOME': os.environ.get('HOME', '/')}
done = subprocess.run([str(a.bmake), '-r', 'MAKECONF=/dev/null', 'PKGSRC_COMPILER=gcc',
                       'CC=gcc', '-V', '${CWRAPPERS_APPEND.cc}'],
                      cwd=a.pkgsrc / 'devel/mkcmd', env=environment, text=True,
                      capture_output=True, timeout=120)
assert done.returncode == 0, done.stdout + done.stderr
output = done.stdout.strip().splitlines()
flags = [flag for flag in shlex.split(output[-1] if output else '') if flag.startswith('-std=')]
assert flags, 'devel/mkcmd does not select a C dialect'

sources = sorted((a.wrksrc / 'bin/mkcmd').glob('*.c'))
assert len(sources) > 10, f'not a mkcmd work source: {a.wrksrc}'
with tempfile.TemporaryDirectory(prefix='mkcmd-c17-', dir=a.work_parent) as temporary:
    for source in sources:
        # The flags of bin/mkcmd/makeme, with the recipe dialect added.
        done = subprocess.run([str(a.cc), *flags, '-O', '-DFREEBSD', '-c', source.name,
                               '-o', str(Path(temporary) / (source.stem + '.o'))],
                              cwd=source.parent, env=environment, text=True,
                              capture_output=True, timeout=300)
        assert done.returncode == 0, f'{source.name}:\n{done.stdout}{done.stderr}'
print(f'PASS: {len(sources)} mkcmd sources compile with {" ".join(flags)}')
