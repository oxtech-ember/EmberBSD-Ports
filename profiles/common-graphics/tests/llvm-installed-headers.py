#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
from pathlib import Path
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'cross'))
import llvm_target

with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    for base in ('prefix', 'source', 'build'):
        for group in ('llvm', 'llvm-c'):
            (root / base / 'include' / group).mkdir(parents=True)
    for group in ('llvm', 'llvm-c'):
        (root / 'source/include' / group / 'public.h').write_text('original\n')
        (root / 'prefix/include' / group / 'public.h').write_text('original\n')
    manifest = root / 'install_manifest.txt'
    manifest.write_text('/usr/pkg/include/llvm/public.h\n/usr/pkg/include/llvm-c/public.h\n')
    proof = llvm_target.installed_headers(root / 'prefix', root / 'source', root / 'build', manifest)
    assert proof == llvm_target.installed_headers(root / 'prefix')
    (root / 'prefix/include/llvm/public.h').unlink()
    try:
        llvm_target.installed_headers(root / 'prefix', root / 'source', root / 'build', manifest)
    except ValueError as exc:
        assert 'header set differs' in str(exc)
    else:
        raise AssertionError('missing public header accepted')
    (root / 'prefix/include/llvm/public.h').write_text('changed\n')
    assert proof != llvm_target.installed_headers(root / 'prefix')
    try:
        llvm_target.installed_headers(root / 'prefix', root / 'source', root / 'build')
    except ValueError as exc:
        assert 'installed LLVM header differs from build' in str(exc)
    else:
        raise AssertionError('changed public header accepted')
print('PASS: installed public header mismatch and later drift refused')
