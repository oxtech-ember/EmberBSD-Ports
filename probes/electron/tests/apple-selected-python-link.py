#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Exercise the Rust linker entry with only the selected Python on PATH."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--source', type=Path, required=True)
p.add_argument('--python', type=Path, required=True)
a = p.parse_args()
assert a.python.is_absolute() and a.python.is_file()
with tempfile.TemporaryDirectory(prefix='electron-linker-python-') as directory:
    root = Path(directory)
    apple = root / 'build/toolchain/apple'
    apple.mkdir(parents=True)
    source = a.source / 'build/toolchain'
    driver = apple / 'linker_driver.py'
    shutil.copy2(source / 'apple/linker_driver.py', driver)
    shutil.copy2(source / 'whole_archive.py', apple.parent / 'whole_archive.py')
    text = driver.read_text()
    assert text.startswith('#!/bin/sh\n')
    assert 'EMBERBSD_HOST_PYTHON:?selected host Python is required' in text
    # No python3 or other executable is present in PATH.
    env = {'PATH': str(root), 'EMBERBSD_HOST_PYTHON': str(a.python)}
    result = subprocess.run([str(driver)], env=env, text=True, capture_output=True)
    assert result.returncode != 0 and 'Usage: linker_driver.py' in result.stderr, result.stderr
    del env['EMBERBSD_HOST_PYTHON']
    result = subprocess.run([str(driver)], env=env, text=True, capture_output=True)
    assert result.returncode != 0 and 'selected host Python is required' in result.stderr, result.stderr
print('selected Python Rust linker entry: PASS')
