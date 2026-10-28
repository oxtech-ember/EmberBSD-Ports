#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check V8 build roll against the upstream transformation and hook layout."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--source', type=Path, required=True)
p.add_argument('--inspector', type=Path, required=True)
p.add_argument('--sdk-source', type=Path, required=True)
a = p.parse_args()
roll = a.source / 'third_party/inspector_protocol/roll.py'
spec = importlib.util.spec_from_file_location('roll', roll)
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
with tempfile.TemporaryDirectory(prefix='v8 inspector roll ') as tmp:
    root = Path(tmp); output = root / 'generated'
    cmd = [sys.executable, str(roll), '--build-source', str(a.inspector),
           '--build-output', str(output), '--build-root', str(root),
           '--build-receipt', str(a.inspector / 'emberbsd-prepared-source.json'),
           '--build-sdk-source', str(a.sdk_source)]
    subprocess.run(cmd, check=True)
    count = 0
    for pattern in module.FILES_TO_SYNC:
        for source in a.inspector.glob(pattern):
            if source.is_file():
                expected = source.read_text().replace('CRDTP_EXPORT ', '').replace('CRDTP_', 'V8_CRDTP_').replace('namespace crdtp', 'namespace v8_crdtp')
                assert (output / source.relative_to(a.inspector)).read_text() == expected
                count += 1
    assert count and json.loads((output / 'ember-v8-inspector-ready.json').read_text())['inspector_tree_sha256']
    for name in ('export.h', 'json_platform_v8.cc', 'test_platform_v8.cc', 'test_platform.h'):
        assert (output / 'crdtp' / name).read_bytes() == (roll.parent / 'crdtp' / name).read_bytes()
    stamp = (output / 'crdtp/span.cc').stat().st_mtime_ns
    subprocess.run(cmd, check=True)
    assert (output / 'crdtp/span.cc').stat().st_mtime_ns == stamp
    orphan = root / '.generated.v8-inspector-stage-interrupted'; orphan.mkdir()
    (orphan / 'unowned').write_text('preserve')
    subprocess.run(cmd, check=True)
    assert (orphan / 'unowned').read_text() == 'preserve'
    backup = root / '.generated.v8-inspector-previous'
    output.rename(backup)
    subprocess.run(cmd, check=True)
    assert output.is_dir() and not backup.exists()
    (output / 'unowned').write_text('preserve')
    assert subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0
    assert (output / 'unowned').read_text() == 'preserve'
    (output / 'unowned').unlink()
    (output / 'empty-unowned').mkdir()
    assert subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0
    assert (output / 'empty-unowned').is_dir()
    (output / 'empty-unowned').rmdir()
    os.mkfifo(output / 'unowned-fifo')
    assert subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0
    assert (output / 'unowned-fifo').exists()
    (output / 'unowned-fifo').unlink()
    invalid = cmd.copy(); invalid[invalid.index('--build-output') + 1] = str(root.parent / 'outside')
    assert subprocess.run(invalid, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0
    invalid = cmd.copy(); invalid[invalid.index('--build-receipt') + 1] = str(root / 'wrong')
    (root / 'wrong').write_text('{}')
    assert subprocess.run(invalid, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0
    module.FILES_TO_SYNC = [x for x in module.FILES_TO_SYNC if x != 'README.md']
    module.BuildRoll(str(a.inspector), str(output), str(root), str(a.inspector / 'emberbsd-prepared-source.json'), str(a.sdk_source))
    assert not (output / 'README.md').exists(), 'stale generated file survived'
    attack = root / 'malicious'; attack.mkdir(); outside = root / 'outside-target'; outside.mkdir()
    (attack / 'crdtp').symlink_to(outside, target_is_directory=True)
    invalid = cmd.copy(); invalid[invalid.index('--build-output') + 1] = str(attack)
    assert subprocess.run(invalid, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0
    assert not list(outside.iterdir()), 'symlink parent permitted a write outside output'
    modified = root / 'modified-source'
    shutil.copytree(a.inspector, modified)
    (modified / 'crdtp/span.cc').write_text('modified payload')
    invalid = cmd.copy(); invalid[invalid.index('--build-source') + 1] = str(modified)
    invalid[invalid.index('--build-receipt') + 1] = str(modified / 'emberbsd-prepared-source.json')
    assert subprocess.run(invalid, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0
    assert (output / 'ember-v8-inspector-ready.json').exists(), 'failed replacement lost previous valid output'
print(f'V8 inspector roll: {count} upstream-equivalent files, hooks, idempotence and boundaries PASS')
