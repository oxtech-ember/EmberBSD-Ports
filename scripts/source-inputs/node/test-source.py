#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Exercise the real Node.js owner against a caller-selected archive and SDK."""
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
    exported = Path(directory) / 'pkgsrc'
    subprocess.run([sys.executable, '-B', str(owner.parents[2] / 'prepare-pkgsrc.py'),
                    str(exported), '--git', str(args.git), '--patch', str(args.patch)], check=True)
    def run(*words, success=True):
        result = subprocess.run([*base, *map(str, words)], capture_output=True, text=True)
        if (result.returncode == 0) != success:
            raise AssertionError(result.stderr)
        return result
    run('prepare', '--archive', args.archive, '--patch', args.patch, '--output', root)
    run('verify-source', '--source', root, '--pkgsrc-root', exported)
    assert (root / 'src/node.cc').is_file()
    assert (root / 'src/node_version.h').is_file()
    assert (root / 'node.gni').is_file()
    run('prepare', '--archive', args.archive, '--patch', args.patch, '--output', root, success=False)
    (root / 'unexpected').write_text('changed\n')
    assert 'payload changed' in run('verify-source', '--source', root, '--pkgsrc-root', exported, success=False).stderr
    (root / 'unexpected').unlink()
    run('verify-source', '--source', root, '--pkgsrc-root', exported)
print('Node.js common prepared source: PASS')
