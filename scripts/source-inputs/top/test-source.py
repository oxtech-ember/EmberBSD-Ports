#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Exercise the real top owner against a caller-selected archive and SDK."""
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
for name in ('sdk-source', 'git', 'patch', 'archive', 'work-dir'):
    parser.add_argument('--' + name, type=Path, required=True)
args = parser.parse_args()
owner = Path(__file__).with_name('source.py')
base = [sys.executable, '-B', str(owner), '--sdk-source', str(args.sdk_source), '--git', str(args.git)]
with tempfile.TemporaryDirectory(dir=args.work_dir) as directory:
    root = Path(directory) / 'prepared'
    def run(*words, success=True):
        result = subprocess.run([*base, *map(str, words)], capture_output=True, text=True)
        if (result.returncode == 0) != success:
            raise AssertionError(result.stderr)
        return result
    run('prepare', '--archive', args.archive, '--patch', args.patch, '--output', root, '--scoped-identity')
    run('verify-source', '--source', root, '--patch', args.patch)
    assert (root / 'top.c').is_file()
    assert (root / 'machine/m_netbsd.c').is_file()
    assert (root / 'machine/m_dragonfly.c').is_file()
    run('prepare', '--archive', args.archive, '--patch', args.patch, '--output', root, success=False)
    invalid = Path(directory) / args.archive.name
    invalid.write_bytes(args.archive.read_bytes() + b'changed')
    assert 'checksum' in run('prepare', '--archive', invalid, '--patch', args.patch,
                             '--output', Path(directory) / 'invalid', success=False).stderr
    (root / 'unexpected').write_text('changed\n')
    assert 'payload changed' in run('verify-source', '--source', root, '--patch', args.patch, success=False).stderr
    (root / 'unexpected').unlink()
    run('verify-source', '--source', root, '--patch', args.patch)
print('top common prepared source: PASS')
