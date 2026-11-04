#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise retry classification and the actual shell workdir transition."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile

script = Path(__file__).resolve().parents[1] / 'cross-bulk.sh'
classifier = script.parent / 'cross-bulk-workdir.py'
text = script.read_text()
fn = text[text.index('prepare_wrkdir()\n'):text.index('\n# Retire successful', text.index('prepare_wrkdir()\n'))]
with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    work = root / 'work'
    work.mkdir()
    obj = work / 'kept.o'
    obj.write_bytes(b'object')
    cookie = work / '.extract_done'
    def run(identity, current, version):
        if identity is None:
            cookie.unlink(missing_ok=True)
        else:
            cookie.write_text(identity + '\n')
        shell = root / 'case.sh'
        shell.write_text('#!/bin/sh\nhost_python="$1"; base=fixture; version="$2"; name="$3"\n'
                         'retire() { mv "$1" "$1.retired"; }\n' + fn +
                         '\nprepare_wrkdir "$4" job\n')
        return subprocess.run(['/bin/sh', str(shell), sys.executable, version, current, str(work)],
                              cwd=script.parent, capture_output=True, text=True)
    # The function resolves the classifier alongside $0.
    (root / 'cross-bulk-workdir.py').write_bytes(classifier.read_bytes())
    obj.unlink()
    assert run(None, 'fixture-1.0nb2', '1.0').returncode == 0
    obj.write_bytes(b'object')
    before = (obj.stat().st_ino, obj.stat().st_mtime_ns)
    assert run('fixture-1.0nb1', 'fixture-1.0nb1', '1.0').returncode == 0
    assert (obj.stat().st_ino, obj.stat().st_mtime_ns) == before
    assert run('fixture-1.0nb1', 'fixture-1.0nb2', '1.0').returncode != 0
    assert (obj.stat().st_ino, obj.stat().st_mtime_ns) == before
    (work / '.build_done').write_text('fixture-1.0nb2\n')
    assert run('fixture-1.0nb1', 'fixture-1.0nb2', '1.0').returncode == 0
    assert (obj.stat().st_ino, obj.stat().st_mtime_ns) == before
    assert run(None, 'fixture-1.0nb2', '1.0').returncode != 0 and obj.exists()
    assert run('fixture-1.0nb2', 'fixture-2.0', '2.0').returncode == 0
    assert not work.exists() and (root / 'work.retired/kept.o').read_bytes() == b'object'
print('PASS: retry preserves objects, unknown fails closed, new version retires')
