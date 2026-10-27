#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Check failed signing leaves its input intact and no temporary file."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess

p = argparse.ArgumentParser(description=__doc__)
for name in ('codesign', 'allocate', 'shell', 'input', 'work'):
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
assert all(getattr(a, name).is_absolute() for name in ('codesign', 'allocate', 'shell', 'input', 'work'))
a.work.mkdir()

def run_case(filename, allocator, error):
    directory = a.work / error
    directory.mkdir()
    target = directory / filename
    shutil.copyfile(a.input, target)
    original = hashlib.sha256(target.read_bytes()).digest()
    env = dict(os.environ, CODESIGN_ALLOCATE=str(allocator))
    result = subprocess.run([str(a.codesign), '-s', '-', '--force', str(target)],
                            env=env, capture_output=True, text=True)
    assert result.returncode != 0 and error in result.stderr
    assert list(directory.iterdir()) == [target]
    assert hashlib.sha256(target.read_bytes()).digest() == original

run_case('input', a.work / 'missing-allocator', 'Failed to spawn codesign_allocate')
failed = a.work / 'failing-allocator'
failed.write_text('#!' + str(a.shell) + '\nexit 9\n')
failed.chmod(0o755)
run_case('input', failed, 'codesign_failed: 9')
run_case('x' * 250, a.allocate, 'mkstemp failed')
print('PASS: signing failure preserves input and removes temporary file')
