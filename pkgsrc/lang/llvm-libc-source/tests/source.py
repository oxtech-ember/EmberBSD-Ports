#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check copied-component identity and detached payload failure controls."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--sdk-source', type=Path, required=True)
p.add_argument('--runtime-source', type=Path, required=True)
a = p.parse_args()
files = Path(__file__).resolve().parents[1] / 'files'
with tempfile.TemporaryDirectory(prefix='llvm-libc receipt ') as tmp:
    root = Path(tmp); runtime = root / 'runtime'; component = runtime / 'libc'
    component.mkdir(parents=True)
    (component / 'header.h').write_text('test component\n')
    shutil.copy2(a.runtime_source / 'llvm-source.json', runtime / 'llvm-source.json')
    staged = root / 'staged'; shutil.copytree(component, staged)
    def run(tool, *args):
        return subprocess.run([sys.executable, '-B', '-I', '-S', str(files / tool),
            '--sdk-source', str(a.sdk_source), *map(str, args)], capture_output=True, text=True)
    stamp = run('stamp-source.py', '--runtime-source', runtime, '--source', staged)
    assert stamp.returncode == 0, stamp.stderr
    ok = run('verify-payload.py', '--source', staged)
    assert ok.returncode == 0 and json.loads(ok.stdout)['package'] == 'lang/llvm-libc-source'
    (staged / 'header.h').write_text('changed\n')
    assert run('verify-payload.py', '--source', staged).returncode != 0
    mismatch = root / 'mismatch'; shutil.copytree(component, mismatch)
    (mismatch / 'header.h').write_text('different\n')
    assert run('stamp-source.py', '--runtime-source', runtime, '--source', mismatch).returncode != 0
    assert not (mismatch / 'emberbsd-prepared-source.json').exists()
print('LLVM libc copied component and payload failure controls PASS')
