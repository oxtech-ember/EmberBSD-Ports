#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Exercise the common zlib owner with the actual recipe and archive."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

parser = argparse.ArgumentParser()
for name in ('sdk-source', 'git', 'patch', 'archive', 'work-dir', 'pkgsrc-export', 'export-patch'):
    parser.add_argument('--' + name, type=Path, required=True)
a = parser.parse_args()
owner = Path(__file__).with_name('source.py')
base = [sys.executable, '-B', str(owner), '--sdk-source', str(a.sdk_source), '--git', str(a.git)]
shared = ['--pkgsrc-export', a.pkgsrc_export, '--export-patch', a.export_patch]
with tempfile.TemporaryDirectory(dir=a.work_dir) as directory:
    directory = Path(directory)
    root = directory / 'source'
    def run(*words, ok=True):
        result = subprocess.run([*base, *map(str, words)], capture_output=True, text=True)
        if (result.returncode == 0) != ok:
            raise AssertionError(result.stderr)
        return result
    run('prepare', '--archive', a.archive, '--patch', a.patch, '--output', root,
        *shared)
    assert (root / 'zlib.h').is_file() and (root / 'LICENSE').is_file()
    assert 'defined(HAVE_UNISTD_H)' in (root / 'zconf.h').read_text()
    assert 'state->past = 0' in (root / 'gzlib.c').read_text()
    run('verify-source', '--source', root, '--patch', a.patch, *shared)
    checker = owner.parents[2] / 'prepared-source-current.py'
    command = [sys.executable, '-B', str(checker), '--sdk-source', str(a.sdk_source),
               '--git', str(a.git), '--patch', str(a.patch), '--source', 'zlib=' + str(root)]
    checked = subprocess.run(command, capture_output=True, text=True)
    assert checked.returncode == 0, checked.stderr
    receipt = root / 'emberbsd-prepared-source.json'
    saved = receipt.read_text()
    stale = json.loads(saved)
    stale['identity']['effective']['effective_package_sha256'] = '0' * 64
    receipt.write_text(json.dumps(stale))
    checked = subprocess.run(command, capture_output=True, text=True)
    assert checked.returncode != 0 and 'stale' in checked.stderr, checked.stderr
    receipt.write_text(saved)
    run('prepare', '--archive', a.archive, '--patch', a.patch, '--output', root,
        *shared, ok=False)
    bad = directory / a.archive.name
    bad.write_bytes(a.archive.read_bytes() + b'invalid')
    assert 'checksum' in run('prepare', '--archive', bad, '--patch', a.patch,
        '--output', directory / 'bad', *shared, ok=False).stderr
    (root / 'unexpected').write_text('modified')
    assert 'payload changed' in run('verify-source', '--source', root,
                                    '--patch', a.patch, ok=False).stderr
    (root / 'unexpected').unlink()
    run('verify-source', '--source', root, '--patch', a.patch)
print('zlib common prepared source PASS')
