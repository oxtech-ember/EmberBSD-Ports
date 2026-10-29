#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Exercise an installed AutoGen tearoff with selected tools and pkgsrc export."""
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
for name in ('sdk-source', 'export', 'host-prefix', 'pkg-admin', 'make', 'makeconf', 'git', 'patch', 'work-dir'):
    parser.add_argument('--' + name, required=True)
parser.add_argument('--make-arg', action='append', default=[])
a = parser.parse_args()
owner = Path(__file__).with_name('source.py')
base = [sys.executable, '-B', str(owner), '--sdk-source', a.sdk_source]
for key in ('export', 'host-prefix', 'pkg-admin', 'make', 'makeconf', 'git', 'patch'):
    base.extend(['--' + key, getattr(a, key.replace('-', '_'))])
for value in a.make_arg:
    base.extend(['--make-arg', value])

def run(*extra, ok=True):
    result = subprocess.run([*base, *map(str, extra)], capture_output=True, text=True)
    if (result.returncode == 0) != ok:
        raise AssertionError(result.stderr or result.stdout)
    return result

with tempfile.TemporaryDirectory(dir=a.work_dir) as tmp:
    source = Path(tmp) / 'source'
    run('--output', source)
    run('--source', source)
    run('--output', source, ok=False)
    (source / 'unexpected').write_text('changed\n')
    run('--source', source, ok=False)
    (source / 'unexpected').unlink()
    run('--source', source)
    run('--make-arg', 'CONFIGURE_ARGS=--changed', '--source', source, ok=False)
print('AutoGen libopts common source: PASS')
