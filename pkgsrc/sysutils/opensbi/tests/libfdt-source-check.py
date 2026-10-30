#!/usr/bin/env python3
"""Verify the firmware producer uses the common libfdt source and SBI env."""
import pathlib
import sys

firmware = pathlib.Path(sys.argv[1]) / 'lib/utils/libfdt'
common = pathlib.Path(sys.argv[2])
files = [p for p in common.iterdir() if p.is_file() and p.suffix in ('.c', '.h')
         and p.name != 'libfdt_env.h']
if not files:
    raise RuntimeError('no common libfdt source files found')
for source in files:
    if source.read_bytes() != (firmware / source.name).read_bytes():
        raise RuntimeError('libfdt producer differs from common source: ' + source.name)
env = (firmware / 'libfdt_env.h').read_text()
if '#include <sbi/sbi_string.h>' not in env or '#include <sbi/sbi_byteorder.h>' not in env:
    raise RuntimeError('firmware is not using the freestanding SBI environment')
print('OpenSBI uses common libfdt sources and its freestanding SBI environment')
