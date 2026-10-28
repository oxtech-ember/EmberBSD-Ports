#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check selected native aliases and their GNU make / native linker roles."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

p = argparse.ArgumentParser(description=__doc__)
for name in ('sdk-source', 'host-prefix', 'work-dir'):
    p.add_argument('--' + name, required=True)
a = p.parse_args()
provider = Path(__file__).resolve().parents[1] / 'cross/prepare-native-tools.py'
with tempfile.TemporaryDirectory(dir=a.work_dir) as tmp:
    output = Path(tmp) / 'aliases'
    command = [sys.executable, '-B', str(provider), '--sdk-source', a.sdk_source,
               'aliases', '--host-prefix', a.host_prefix, '--output', str(output)]
    result = json.loads(subprocess.check_output(command))
    assert result['path'].split(os.pathsep)[0] == str(output)
    for name, suffix in [('awk', 'nawk'), ('make', 'gmake'), ('ar', 'llvm-ar'),
                         ('ranlib', 'llvm-ranlib'), ('ld', 'ld64.lld')]:
        assert (output / name).is_symlink()
        assert Path(os.readlink(output / name)).name == suffix
    assert subprocess.check_output(command)
    (output / 'make').unlink()
    (output / 'make').symlink_to('/usr/bin/make')
    assert subprocess.run(command, stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL).returncode != 0
print('Selected native host phase aliases: PASS')
