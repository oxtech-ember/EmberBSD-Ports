#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Query Mesa's target LLVM selection using a real common cross MAKECONF."""
import argparse
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser()
for name in ('pkgsrc', 'makeconf', 'bmake'):
    parser.add_argument('--' + name, type=Path, required=True)
args = parser.parse_args()
base = [str(args.bmake), '-C', str(args.pkgsrc / 'graphics/MesaLib'),
        'MAKECONF=' + str(args.makeconf)]
names = 'PKG_FAIL_REASON EMBERBSD_GRAPHICS_LLVM_CONFIG LLVM_CONFIG_PATH MESON_BINARY.llvm-config'
def query(extra):
    result = subprocess.run(base + extra + ['show-vars', 'VARNAMES=' + names],
                            check=True, capture_output=True, text=True, timeout=45)
    values = result.stdout.splitlines()
    assert len(values) == 4, values
    return values
full = query([])
assert not full[0] and full[1].endswith('/helper/bin/llvm-config') and full[1] == full[2] == full[3], full
soft = query(['PKG_OPTIONS.MesaLib=softpipe-only x11 -llvm -wayland'])
assert soft == ['', '', '', ''], soft
explicit = '/tmp/fixture/llvm-config'
selected = query(['EMBERBSD_GRAPHICS_LLVM_CONFIG=' + explicit])
assert not selected[0] and selected[1:] == [explicit] * 3, selected
result = subprocess.run(base + ['EMBERBSD_GRAPHICS_LLVM_CONFIG=' + explicit,
    'LLVM_CONFIG_PATH=/wrong/llvm-config', 'emberbsd-graphics-llvm-input-check'],
    capture_output=True, text=True, timeout=45)
assert result.returncode and 'overridden LLVM_CONFIG_PATH' in result.stdout + result.stderr
with tempfile.TemporaryDirectory(prefix='mesa-route-') as temp:
    config = Path(temp) / 'mk.conf'
    config.write_text('LLVM_CONFIG_PATH=/wrong/llvm-config\n.include "' + str(args.makeconf) + '"\n')
    result = subprocess.run([str(args.bmake), '-C', str(args.pkgsrc / 'graphics/MesaLib'),
        'MAKECONF=' + str(config), 'EMBERBSD_GRAPHICS_LLVM_CONFIG=' + explicit,
        'emberbsd-graphics-llvm-input-check'], capture_output=True, text=True, timeout=45)
    assert result.returncode and 'earlier conflicting LLVM_CONFIG_PATH' in result.stdout + result.stderr
print('PASS: standalone full, softpipe, explicit and conflicting LLVM routes')
