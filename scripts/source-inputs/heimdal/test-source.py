#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Exercise the real heimdal owner against a caller-selected archive and SDK."""
import argparse
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
for name in ('sdk-source', 'git', 'patch', 'archive', 'work-dir', 'pkgsrc-export'):
    parser.add_argument('--' + name, type=Path, required=True)
args = parser.parse_args()
owner = Path(__file__).with_name('source.py')
base = [sys.executable, '-B', str(owner), '--sdk-source', str(args.sdk_source), '--git', str(args.git)]
with tempfile.TemporaryDirectory(dir=args.work_dir) as directory:
    root = Path(directory) / 'prepared'
    def run(*words, success=True):
        result = subprocess.run([*base, *map(str, words), '--pkgsrc-export', str(args.pkgsrc_export)], capture_output=True, text=True)
        if (result.returncode == 0) != success:
            raise AssertionError(result.stderr)
        return result
    run('prepare', '--archive', args.archive, '--patch', args.patch, '--output', root, '--scoped-identity')
    run('verify-source', '--source', root, '--patch', args.patch)
    bad = Path(directory) / args.archive.name
    shutil.copyfile(args.archive, bad)
    with bad.open('r+b') as stream:
        byte = stream.read(1)
        stream.seek(0)
        stream.write(bytes([byte[0] ^ 1]))
    run('prepare', '--archive', bad, '--patch', args.patch, '--output', Path(directory) / 'bad', success=False)
    assert (root / 'configure').is_file()
    assert (root / 'lib/hx509/cert.c').is_file()
    assert (root / 'lib/hcrypto/heim_find_prime.h').is_file()
    assert (root / 'lib/hcrypto/heim_find_prime.h').read_bytes() == (
        args.pkgsrc_export / 'pkgsrc/security/heimdal/files/heim_find_prime.h').read_bytes()
    patch_file = args.pkgsrc_export / 'pkgsrc/security/heimdal/patches/patch-configure'
    original = patch_file.read_bytes()
    try:
        patch_file.write_bytes(original + b'\ncorrupt patch\n')
        result = run('prepare', '--archive', args.archive, '--patch', args.patch,
                     '--output', Path(directory) / 'bad-patch', success=False)
        assert 'patch checksum differs' in result.stderr
    finally:
        patch_file.write_bytes(original)
    run('prepare', '--archive', args.archive, '--patch', args.patch, '--output', root, success=False)
    (root / 'unexpected').write_text('changed\n')
    assert 'payload changed' in run('verify-source', '--source', root, '--patch', args.patch, success=False).stderr
    (root / 'unexpected').unlink()
    run('verify-source', '--source', root, '--patch', args.patch)
print('heimdal common prepared source: PASS')
