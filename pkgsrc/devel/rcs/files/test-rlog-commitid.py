#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Check rlog -c with a real CVS-created RCS archive."""
import argparse
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser()
p.add_argument('--binary', required=True, type=Path)
p.add_argument('--archive', required=True, type=Path)
p.add_argument('--explicit', action='store_true')
p.add_argument('--work-dir', required=True, type=Path)
a = p.parse_args()
binary = a.binary.resolve(strict=True)
archive = a.archive.resolve(strict=True)

def run(*args):
    return subprocess.run([str(binary), 'rlog', *args, str(archive)],
                          check=True, capture_output=True, text=True).stdout

with tempfile.TemporaryDirectory(dir=a.work_dir) as directory:
    target = Path(directory) / 'sample,v'
    target.write_bytes(archive.read_bytes())
    archive = target
    normal, selected = run(), run('-c')
marker = 'commitid: aPcoov2EuHte33su'
if marker not in selected or (marker in normal) == a.explicit:
    raise AssertionError('rlog commit identifier policy differs')
if a.explicit and marker + ';' not in selected:
    raise AssertionError('rlog -c lost the historical output terminator')
print('RCS rlog commit identifier selection: PASS')
