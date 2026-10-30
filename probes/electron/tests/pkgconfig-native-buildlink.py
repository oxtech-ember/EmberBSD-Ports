#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise Chromium's selected native buildlink pkgconf routing."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
for name in ('source', 'patch', 'pkgconf', 'view'):
    parser.add_argument('--' + name, type=Path, required=True)
a = parser.parse_args()
owner = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='electron-pkgconfig-buildlink-') as directory:
    root = Path(directory)
    for name in ('build/config/BUILDCONFIG.gn', 'build/config/linux/pkg_config.gni',
                 'build/config/linux/pkg-config.py'):
        dest = root / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(a.source / name, dest)
    subprocess.run([str(a.patch), '--batch', '--fuzz=0', '-p1', '-i',
                    str(owner / 'patches/gn-pkgconfig-native-buildlink.patch')],
                   cwd=root, check=True, stdout=subprocess.PIPE)
    script = root / 'build/config/linux/pkg-config.py'
    base = [sys.executable, str(script), '-p', str(a.pkgconf)]
    selected = base + ['--emberbsd-native-prefix', str(a.view),
                       '--emberbsd-native-buildlink']
    env = dict(os.environ, PKG_CONFIG_PATH='/invalid/poison',
               PKG_CONFIG_LIBDIR='/invalid/poison', PKG_CONFIG_SYSROOT_DIR='/invalid/poison')
    def run(argv):
        return subprocess.run(argv, text=True, capture_output=True, check=True, env=env).stdout.strip()
    flags = run(selected + ['protobuf', 'zlib'])
    assert str(a.view / 'include') in flags and str(a.view / 'lib') in flags, flags
    assert run(selected + ['--libdir', 'protobuf']) == str(a.view / 'lib')
    assert run(selected + ['--atleast-version', '36.2', 'protobuf']) == 'true'
    assert run(selected + ['--version-as-components', 'protobuf'])
    invalid = subprocess.run(base + ['--emberbsd-native-buildlink', 'protobuf'],
                             text=True, capture_output=True)
    assert invalid.returncode != 0 and 'requires a selected prefix' in invalid.stderr
print('Native buildlink pkg-config routing PASS')
