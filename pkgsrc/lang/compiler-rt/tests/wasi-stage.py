#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check WASI builtins stage and reject changed or missing archive bytes."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys

parser = argparse.ArgumentParser(description=__doc__)
for name in ('sdk-source', 'source', 'stage', 'work'):
    parser.add_argument('--' + name, type=Path, required=True)
parser.add_argument('--pkgsrc-root', type=Path)
parser.add_argument('--git', type=Path)
a = parser.parse_args()
work = a.work
if not work.is_absolute() or work.exists():
    parser.error('work must be an absolute new directory')
work.mkdir()
owner = Path(__file__).resolve().parents[1] / 'files/runtime.py'
command = [sys.executable, '-B', '-S', str(owner), '--sdk-source', str(a.sdk_source)]
if a.pkgsrc_root:
    command += ['--pkgsrc-root', str(a.pkgsrc_root)]
command += ['wasi-verify', '--source', str(a.source)]
if a.git:
    command += ['--git', str(a.git)]


def verify(stage, success):
    result = subprocess.run([*command, '--stage', str(stage)], capture_output=True, text=True)
    if (result.returncode == 0) != success:
        raise RuntimeError(result.stderr)
    return result


verify(a.stage, True)
copy = work / 'stage'
shutil.copytree(a.stage, copy)
archive = copy / 'lib/wasm32-unknown-wasip1/libclang_rt.builtins.a'
data = archive.read_bytes()
archive.write_bytes(data + b'changed')
assert 'stage changed' in verify(copy, False).stderr
archive.unlink()
assert 'archive is missing' in verify(copy, False).stderr
archive.write_bytes(data)
verify(copy, True)
print('WASI builtins stage, changed/missing archive controls: PASS')
