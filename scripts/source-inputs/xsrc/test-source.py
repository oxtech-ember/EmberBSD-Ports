#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Exercise the real xsrc owner against a caller-selected archive and SDK."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
for name in ('sdk-source', 'archive', 'patch', 'work-dir'):
    parser.add_argument('--' + name, type=Path, required=True)
args = parser.parse_args()
owner = Path(__file__).with_name('source.py')
base = [sys.executable, '-B', str(owner), '--sdk-source', str(args.sdk_source)]
with tempfile.TemporaryDirectory(dir=args.work_dir) as directory:
    directory = Path(directory)
    root = directory / 'prepared'
    def run(*words, success=True):
        result = subprocess.run([*base, *map(str, words)], capture_output=True, text=True)
        if (result.returncode == 0) != success:
            raise AssertionError(result.stderr)
        return result
    # A changed archive with the pinned name is refused before extraction.
    changed = directory / 'changed' / 'xsrc.tgz'
    changed.parent.mkdir()
    shutil.copyfile(args.archive, changed)
    with changed.open('ab') as handle:
        handle.write(b'\0')
    assert 'checksum differs' in run('prepare', '--archive', changed, '--output', root,
                                     '--patch', args.patch, success=False).stderr
    assert not root.exists()
    # The EmberBSD patches are part of the source contract.
    assert 'absolute patch tool' in run('prepare', '--archive', args.archive, '--output', root,
                                        success=False).stderr
    assert not root.exists()
    record = json.loads(run('prepare', '--archive', args.archive, '--output', root,
                            '--patch', args.patch).stdout)
    assert record['package'] == 'netbsd/xsrc'
    assert record['identity'] == json.loads(run('pin').stdout)
    run('verify-source', '--source', root)
    assert (root / 'external/mit/libX11/dist/configure.ac').is_file()
    assert (root / 'external/mit/xorg-server/dist/configure.ac').is_file()
    assert not (root / 'CVS').exists() and not (root / 'external/CVS').exists()
    assert sorted(record['identity']['patches']) == sorted(p.name for p in owner.with_name('patches').glob('*.patch'))
    assert 'xcb_setup_generic_t header;' in (root / 'external/mit/libxcb/dist/src/xcb_conn.c').read_text()
    assert not any(p.name.endswith(('.orig', '.rej')) for p in (root / 'external/mit/MesaLib/dist/src').rglob('*'))
    run('prepare', '--archive', args.archive, '--output', root, '--patch', args.patch, success=False)
    (root / 'unexpected').write_text('changed\n')
    assert 'payload changed' in run('verify-source', '--source', root, success=False).stderr
    (root / 'unexpected').unlink()
    run('verify-source', '--source', root)
print('xsrc prepared source: PASS')
