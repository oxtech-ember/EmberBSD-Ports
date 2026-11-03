#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Exercise the actual LLVM package selector.
import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('--sdk-source', type=Path, required=True)
args = parser.parse_args()
helper = Path(__file__).resolve().parents[3] / 'pkgsrc/lang/llvm/files/select-package-stage.py'
sdk = args.sdk_source.resolve(strict=True)
with tempfile.TemporaryDirectory(prefix='llvm-stage-handoff-') as tmp:
    root = Path(tmp)
    shared = root / 'shared'
    def manifest(header):
        for name, rows in {'full': ['lib/runtime.so', header],
                           'runtime': ['lib/runtime.so'], 'devel': [header]}.items():
            (root / name).write_text(''.join(row + '\n' for row in rows))
    def stage(name, header, runtime, contents):
        path = root / name
        (path / 'lib').mkdir(parents=True)
        (path / 'include').mkdir()
        (path / 'lib/runtime.so').write_text(runtime)
        (path / header).write_text(contents)
        return path
    def call(operation, *items, success=True):
        result = subprocess.run([sys.executable, '-B', str(helper), '--sdk-source', str(sdk),
                                 operation, *map(str, items)], capture_output=True, text=True)
        if (result.returncode == 0) != success:
            raise AssertionError(f'{operation}: rc={result.returncode}: {result.stdout}{result.stderr}')
    def handoff(path, destination, success=True):
        call('handoff-runtime', path, root/'full', root/'runtime', root/'devel',
             root/'runtime', destination, success=success)
    def copy_devel(name):
        dest = root / name
        call('copy-devel', shared, dest, root/'full', root/'runtime', root/'devel', root/'devel')
        return dest
    manifest('include/old.h')
    first = stage('first', 'include/old.h', 'old runtime', 'old header')
    handoff(first, shared)
    same = stage('same', 'include/old.h', 'new runtime', 'new header')
    handoff(same, shared)
    devel = copy_devel('devel-same')
    assert (same/'lib/runtime.so').read_text() == 'new runtime'
    assert (shared/'include/old.h').read_text() == 'new header'
    assert (devel/'include/old.h').read_text() == 'new header'
    manifest('include/new.h')
    changed = stage('changed', 'include/new.h', 'third runtime', 'third header')
    handoff(changed, shared)
    devel = copy_devel('devel-changed')
    assert (changed/'lib/runtime.so').read_text() == 'third runtime'
    assert (shared/'include/new.h').read_text() == 'third header'
    assert (devel/'include/new.h').read_text() == 'third header'
    assert not (shared/'include/old.h').exists() and not (devel/'include/old.h').exists()
    alias = root/'alias'
    os.symlink(shared, alias)
    for index, destination in enumerate(('/', '/.', str(alias))):
        candidate = stage('unsafe-' + str(index), 'include/new.h', 'intact', 'intact header')
        handoff(candidate, destination, success=False)
        assert (candidate/'lib/runtime.so').read_text() == 'intact'
        assert (candidate/'include/new.h').read_text() == 'intact header'
        assert (shared/'include/new.h').read_text() == 'third header'
    overlap = stage('overlap', 'include/new.h', 'intact', 'intact header')
    handoff(overlap, overlap/'nested', success=False)
    assert (overlap/'lib/runtime.so').read_text() == 'intact'
    assert (overlap/'include/new.h').read_text() == 'intact header'
print('LLVM shared-stage handoff: PASS')
