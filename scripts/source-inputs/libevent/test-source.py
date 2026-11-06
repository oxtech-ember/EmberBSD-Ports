#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Exercise the real libevent owner against a caller-selected archive and SDK."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
for name in ('sdk-source', 'git', 'patch', 'archive', 'work-dir'):
    parser.add_argument('--' + name, type=Path, required=True)
parser.add_argument('--pkgsrc-export', type=Path)
parser.add_argument('--export-patch', type=Path)
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
    shared = []
    if args.pkgsrc_export:
        shared += ['--pkgsrc-export', args.pkgsrc_export]
    if args.export_patch:
        shared += ['--export-patch', args.export_patch]
    # An owner change requires comparison with the current prepared payload.
    run('prepare', '--archive', args.archive, '--patch', args.patch, '--output', root, *shared)
    receipt = root / 'emberbsd-prepared-source.json'
    record = json.loads(receipt.read_text())
    assert record['identity']['effective']['api'] == 3
    record['identity']['owner_sha256'] = '0' * 64
    receipt.write_text(json.dumps(record))
    payload = root / 'event.c'
    before = (payload.read_bytes(), payload.stat().st_mtime_ns, payload.stat().st_ino)
    run('refresh-source', '--source', root, '--archive', args.archive, '--patch', args.patch, *shared)
    refreshed = json.loads(receipt.read_text())
    assert refreshed['identity']['effective']['api'] == 3
    assert (payload.read_bytes(), payload.stat().st_mtime_ns, payload.stat().st_ino) == before
    assert (root / 'include/event2/event.h').is_file()
    assert (root / 'test/regress.c').is_file()
    run('prepare', '--archive', args.archive, '--patch', args.patch, '--output', root, *shared, success=False)
    (root / 'unexpected').write_text('changed\n')
    receipt_before = receipt.read_bytes()
    assert 'payload changed' in run('refresh-source', '--source', root, '--archive', args.archive,
                                    '--patch', args.patch, *shared, success=False).stderr
    assert receipt.read_bytes() == receipt_before
    (root / 'unexpected').unlink()
    run('verify-source', '--source', root, '--patch', args.patch, *shared)
print('libevent common prepared source: PASS')
