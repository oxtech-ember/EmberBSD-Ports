#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Compile the shared LZMA decoder with caller-selected Clang and no libc."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', required=True, type=Path)
parser.add_argument('--clang', required=True, type=Path)
parser.add_argument('--resource-dir', required=True, type=Path)
args = parser.parse_args()
for path in (args.source, args.clang, args.resource_dir):
    if not path.is_absolute():
        parser.error('paths must be absolute')
with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as temporary:
    root = Path(temporary)
    glue = root / 'glue.h'
    glue.write_text('void *memcpy(void *, const void *, __SIZE_TYPE__);\n')
    subprocess.run([str(args.clang), '--target=aarch64-unknown-none-elf',
                    '-ffreestanding', '-nostdinc', '-isystem',
                    str(args.resource_dir / 'include'), '-DZ7_FREESTANDING',
                    '-DZ7_LZMA_SIZE_OPT', '-include', str(glue), '-Werror',
                    '-c', str(args.source / 'C/LzmaDec.c'), '-o', str(root / 'decoder.o')],
                   env={'PATH': str(args.clang.parent)}, check=True)
print('7-Zip freestanding decoder compile: PASS')
