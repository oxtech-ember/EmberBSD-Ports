#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Inject allocation failures into actual libplist parser and serializer sources."""
import argparse
from pathlib import Path
import subprocess

p = argparse.ArgumentParser(description=__doc__)
for name in ('source', 'build', 'clang', 'sdk', 'work'):
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
assert all(getattr(a, n).is_absolute() for n in ('source', 'build', 'clang', 'sdk', 'work'))
a.work.mkdir()
flags = ['-isysroot', str(a.sdk), '-DHAVE_CONFIG_H', '-I' + str(a.build),
         '-I' + str(a.source / 'include'), '-I' + str(a.source / 'src'),
         '-I' + str(a.source / 'libcnary/include')]
objects = []
for name in ('oplist', 'jplist'):
    output = a.work / (name + '.o')
    subprocess.run([str(a.clang), *flags, '-Dmalloc=plist_test_malloc', '-c',
                    str(a.source / 'src' / (name + '.c')), '-o', str(output)], check=True)
    objects.append(output)
program = a.work / 'oom-test'
subprocess.run([str(a.clang), '-isysroot', str(a.sdk), '-I' + str(a.source / 'include'),
                str(Path(__file__).with_name('oom.c')), *map(str, objects),
                str(a.build / 'src/.libs/libplist-2.0.a'), '-o', str(program)], check=True)
for case in ('json', 'jsonuid', 'jsonreal', 'ostep', 'ostepuid', 'ostepreal', 'parse'):
    subprocess.run([str(program), case], check=True)
print('PASS: seven real-source allocation failure cases')
