#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Exercise the optional state field allowed by the RCS file grammar."""
import argparse
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser()
p.add_argument('--binary', required=True, type=Path)
p.add_argument('--archive', required=True, type=Path)
p.add_argument('--work-dir', required=True, type=Path)
a = p.parse_args()
binary = a.binary.resolve(strict=True)
fixture = a.archive.read_bytes()
if fixture.count(b'state Exp;') != 1:
    raise ValueError('unexpected fixture')
with tempfile.TemporaryDirectory(dir=a.work_dir) as temporary:
    archive = Path(temporary) / 'sample,v'
    archive.write_bytes(fixture.replace(b'state Exp;', b'state ;'))
    def run(*args):
        command = args[1:] if args[0] == 'rcs' else args
        return subprocess.run([str(binary), *command, str(archive)],
                              check=True, capture_output=True, text=True).stdout
    if 'state: ;' not in run('rlog'):
        raise AssertionError('empty state was not displayed')
    if '# The "rcsinfo" file' not in run('co', '-p', '-q'):
        raise AssertionError('checkout of empty state failed')
    run('rcs', '-q', '-sExp:1.1')
    if 'state: Exp;' not in run('rlog'):
        raise AssertionError('state update was not retained')
print('RCS optional state read, checkout and update: PASS')
