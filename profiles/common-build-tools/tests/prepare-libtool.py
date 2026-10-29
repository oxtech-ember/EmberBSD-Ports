#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Check cross-libtool producer destination and family boundaries."""
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile

p = argparse.ArgumentParser(description=__doc__)
for name in ('sdk-source', 'host-prefix', 'sysroot', 'git', 'work-dir', 'python'):
    p.add_argument('--' + name, required=True)
a = p.parse_args()
producer = Path(__file__).resolve().parents[1] / 'cross/prepare-libtool.py'
python = Path(a.python)
with tempfile.TemporaryDirectory(dir=a.work_dir) as temp:
    root = Path(temp)
    tools = root / 'tools'
    tools.mkdir()
    existing = tools / 'existing'
    existing.mkdir()
    marker = existing / 'marker'
    marker.write_text('preserve')
    base = [str(python), '-B', str(producer), '--sdk-source', a.sdk_source,
            '--host-prefix', a.host_prefix, '--compiler', a.host_prefix,
            '--os-tools', str(tools), '--sysroot', a.sysroot,
            '--work-parent', a.work_dir, '--git', a.git, '--target', 'aarch64']
    def reject(*args):
        result = subprocess.run([*base, *map(str, args)], capture_output=True, text=True)
        assert result.returncode, result.stdout
        return result.stderr
    assert 'incompatible cross-libtool output' in reject('--output', existing)
    assert marker.read_text() == 'preserve'
    outside = root / 'outside'
    assert 'inside the selected OS TOOLDIR' in reject('--output', outside)
    assert not outside.exists()
    sys.path.insert(0, str(Path(a.sdk_source) / 'src'))
    from emberbsd_sdk.process import ContextLocks
    lock_root = root / 'locks'
    lock_root.mkdir()
    locked = tools / 'locked'
    with ContextLocks([str(Path(a.host_prefix).resolve()),
                       str(Path(a.host_prefix).resolve() / 'var/db/pkg')], str(lock_root)):
        assert 'busy' in reject('--output', locked, '--lock-directory', lock_root)
    assert not locked.exists()
    invalid = tools / 'wrong-family'
    assert '--runtime-stage requires Clang' in reject('--output', invalid,
           '--compiler-family', 'gcc', '--runtime-stage', a.sysroot)
    assert not invalid.exists()
    invalid_base = tools / 'base-without-stage'
    assert '--runtime-base requires --runtime-stage' in reject('--output', invalid_base,
           '--runtime-base', a.sysroot)
    assert not invalid_base.exists()
print('cross-libtool producer destination/family boundaries: PASS')
