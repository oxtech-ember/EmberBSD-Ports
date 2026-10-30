#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check Electron's resource version against the selected host compiler."""
import argparse
import importlib.util
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser()
p.add_argument('--host-prefix', type=Path, required=True)
args = p.parse_args()
owner = Path(__file__).resolve().parents[1] / 'electron44/files/build-electron.py'
spec = importlib.util.spec_from_file_location('electron_build', owner)
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)
prefix = args.host_prefix.resolve(strict=True)
result = subprocess.run([str(prefix / 'bin/clang'), '-print-resource-dir'],
                        env={'PATH': str(prefix / 'bin')}, check=True,
                        capture_output=True, text=True)
resource = Path(result.stdout.strip()).resolve(strict=True)
assert build.clang_resource_version(prefix, str(resource)) == resource.name
with tempfile.TemporaryDirectory(prefix='electron-clang-resource-') as temp:
    root = Path(temp)
    good = root / 'prefix/lib/clang/91'
    (good / 'include').mkdir(parents=True)
    assert build.clang_resource_version(root / 'prefix', str(good)) == '91'
    outside = root / 'outside/91'
    (outside / 'include').mkdir(parents=True)
    (root / 'prefix/lib/clang/91').rename(root / 'prefix/lib/clang/old')
    (root / 'prefix/lib/clang/91').symlink_to(outside, target_is_directory=True)
    try:
        build.clang_resource_version(root / 'prefix', str(outside))
    except ValueError:
        pass
    else:
        raise AssertionError('accepted resource symlink escaping prefix')
    try:
        build.clang_resource_version(root / 'prefix', 'lib/clang/91')
    except ValueError:
        pass
    else:
        raise AssertionError('accepted relative resource directory')
    try:
        build.clang_resource_version(root / 'prefix', '')
    except ValueError:
        pass
    else:
        raise AssertionError('accepted empty resource directory')
print('selected Clang resource and invalid cases PASS')
