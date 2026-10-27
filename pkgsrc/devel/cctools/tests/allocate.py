#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Exercise real thin and universal Mach-O signature allocation."""
import argparse
from pathlib import Path
import subprocess

p = argparse.ArgumentParser(description=__doc__)
for name in ('clang', 'lipo', 'objdump', 'allocate', 'sdk', 'work'):
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
assert all(getattr(a, n).is_absolute() for n in ('clang', 'lipo', 'objdump', 'allocate', 'sdk', 'work'))
a.work.mkdir()
src = a.work / 'main.c'
src.write_text('int main(void) { return 0; }\n')

def run(*args):
    return subprocess.run([str(x) for x in args], check=True, capture_output=True, text=True)

for arch in ('arm64', 'x86_64'):
    run(a.clang, '-target', arch + '-apple-macos12', '-isysroot', a.sdk,
        '-fuse-ld=lld', '-nostdlib', '-Wl,-e,_main', src, '-o', a.work / arch)
run(a.lipo, '-create', a.work / 'arm64', a.work / 'x86_64', '-output', a.work / 'fat')
run(a.allocate, '-i', a.work / 'arm64', '-a', 'arm64', '4096', '-o', a.work / 'thin-out')
run(a.allocate, '-i', a.work / 'fat', '-a', 'arm64', '4096', '-a', 'x86_64', '4096', '-o', a.work / 'fat-out')
for filename, count in (('thin-out', 1), ('fat-out', 2)):
    output = run(a.objdump, '--macho', '--arch=all', '--private-headers', a.work / filename).stdout
    assert output.count('LC_CODE_SIGNATURE') == count
    assert output.count('datasize 4096') == count
print('PASS: thin and universal Mach-O allocations')
