#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Query the common libdrm recipe using the actual cross make configuration."""
import argparse
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
for name in ('pkgsrc', 'makeconf', 'bmake'):
    parser.add_argument('--' + name, type=Path, required=True)
args = parser.parse_args()
base = [str(args.bmake), '-C', str(args.pkgsrc / 'x11/libdrm'),
        'MAKECONF=' + str(args.makeconf)]
for option, expected in (('', '-Dtests=false'), ('tests', '-Dtests=true')):
    output = subprocess.run(base + ['PKG_OPTIONS.libdrm=' + option, 'show-vars',
                                   'VARNAMES=PKG_FAIL_REASON MESON_ARGS'],
                            check=True, capture_output=True, text=True, timeout=45).stdout.splitlines()
    assert not output[0].strip(), output
    assert expected in output[1].split(), output
    assert '-Dinstall-test-programs=false' in output[1].split(), output
result = subprocess.run(base + ['-n', 'pre-test'], check=True, capture_output=True, text=True, timeout=45)
assert 'Enable the tests package option' in result.stdout and 'false' in result.stdout
print('PASS: common cross libdrm selects tests only on request')
