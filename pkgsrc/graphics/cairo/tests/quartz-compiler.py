#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted cairo Darwin Quartz compiler regression.
"""Evaluate the cairo options with real bmake and pkgsrc for GCC and Clang.

The Quartz framework headers use Apple blocks. GCC cannot parse them, so a
GCC build on Darwin must not select the quartz option.
"""
import argparse
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--bmake', required=True, type=Path)
parser.add_argument('--pkgsrc', required=True, type=Path, help='a pkgsrc tree with mk/')
parser.add_argument('--work-parent', required=True, type=Path)
a = parser.parse_args()
recipe = Path(__file__).resolve().parents[1]

if platform.system() != 'Darwin' or not Path(
        '/System/Library/Frameworks/Quartz.framework').exists():
    print('SKIP: the quartz option exists only on Darwin with Quartz.framework')
    sys.exit(0)

with tempfile.TemporaryDirectory(prefix='cairo-quartz-', dir=a.work_parent) as temporary:
    root = Path(temporary)
    # Overlay only this recipe's options on the real tree; its includes stay real.
    source = a.pkgsrc.resolve()
    for entry in source.iterdir():
        if entry.name != 'graphics':
            (root / entry.name).symlink_to(entry)
    for entry in (source / 'graphics').iterdir():
        if entry.name != 'cairo':
            (root / 'graphics').mkdir(exist_ok=True)
            (root / 'graphics' / entry.name).symlink_to(entry)
    package = root / 'graphics/cairo'
    package.mkdir(parents=True)
    (package / 'options.mk').write_bytes((recipe / 'options.mk').read_bytes())
    (package / 'Makefile').write_text('.include "options.mk"\nall:\n')

    def evaluate(compiler, options=None):
        command = [str(a.bmake), '-r', 'MAKECONF=/dev/null',
                   f'PKGSRC_COMPILER={compiler}',
                   '-V', '${PKG_SUPPORTED_OPTIONS}|${PKG_OPTIONS}|${MESON_ARGS:M-Dquartz*}']
        if options is not None:
            command.append(f'PKG_OPTIONS.cairo={options}')
        environment = {'PATH': os.environ.get('PATH', '/usr/bin:/bin'),
                       'HOME': os.environ.get('HOME', '/')}
        done = subprocess.run(command, cwd=package, env=environment, text=True,
                              capture_output=True, timeout=120)
        return done.returncode, done.stdout.strip().splitlines()[-1:], done.stdout + done.stderr

    rc, last, out = evaluate('gcc')
    assert rc == 0 and last, out
    supported, selected, quartz = (field.split() for field in last[0].split('|'))
    assert 'quartz' not in supported and 'quartz' not in selected, out
    assert 'x11' not in selected and quartz == ['-Dquartz=disabled'], out
    rc, last, out = evaluate('ccache gcc')
    assert rc == 0 and last and '-Dquartz=disabled' in last[0], out
    # An explicit request cannot select an option that GCC builds do not support.
    rc, last, out = evaluate('gcc', 'quartz')
    assert rc == 0 and last and last[0].endswith('|-Dquartz=disabled'), out
    rc, last, out = evaluate('clang')
    assert rc == 0 and last, out
    supported, selected, quartz = (field.split() for field in last[0].split('|'))
    assert 'quartz' in supported and 'quartz' in selected, out
    assert quartz == ['-Dquartz=enabled'], out
print('PASS: 4 cairo Darwin compiler option evaluations with real bmake')
