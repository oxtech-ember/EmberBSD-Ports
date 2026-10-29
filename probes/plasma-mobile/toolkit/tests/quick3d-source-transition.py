#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Check safe source transition and preservation of local changes."""
import importlib.util
from pathlib import Path
import tarfile
import tempfile
import sys

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('quick3d_transition', root/'cross/quick3d-source-transition.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
if len(sys.argv) != 2 or not Path(sys.argv[1]).is_absolute():
    raise SystemExit('usage: quick3d-source-transition.py ABSOLUTE_PATCH')
patch = sys.argv[1]
with tempfile.TemporaryDirectory(prefix='qt-source-transition-') as tmp:
    p = Path(tmp); source = p/'qtquick3d-everywhere-src-6.12.0'; (source/'src').mkdir(parents=True)
    f = source/'src/test.txt'; f.write_text('one\ntwo\n')
    archive = p/'qt.tar.xz'
    with tarfile.open(archive, 'w:xz') as tar: tar.add(source, arcname=source.name)
    patchfile = p/'owner.patch'; patchfile.write_text('--- src/test.txt.orig\n+++ src/test.txt\n@@ -1,2 +1,2 @@\n one\n-two\n+three\n')
    marker = p/'proof'; args = (source, archive, marker, patch, [patchfile])
    m.transition(*args, plan=True)
    assert f.read_text() == 'one\ntwo\n' and not marker.exists()
    f.write_text('local change\n')
    try: m.transition(*args)
    except ValueError as e: assert 'differs from upstream' in str(e)
    else: raise AssertionError('local edit accepted')
    assert f.read_text() == 'local change\n' and not marker.exists()
    # An interruption after patching but before the marker must be resumable.
    f.write_text('one\nthree\n'); m.transition(*args)
    assert marker.exists()
    marker.unlink()
    # Likewise when another target remains unapplied.
    second = source/'src/second.txt'; second.write_text('old\n')
    with tarfile.open(archive, 'w:xz') as tar:
        f.write_text('one\ntwo\n'); tar.add(source, arcname=source.name)
    f.write_text('one\nthree\n')
    second_patch = p/'second.patch'; second_patch.write_text('--- src/second.txt.orig\n+++ src/second.txt\n@@ -1 +1 @@\n-old\n+new\n')
    args = (source, archive, marker, patch, [patchfile, second_patch])
    m.transition(*args)
    assert second.read_text() == 'new\n'
    assert f.read_text() == 'one\nthree\n' and marker.exists()
    m.transition(*args)
    f.write_text('changed after patch\n')
    try: m.transition(*args)
    except ValueError as e: assert 'patched source changed' in str(e)
    else: raise AssertionError('modified patched source accepted')
print('PASS: dry run, local edit preservation, apply and resume integrity')
