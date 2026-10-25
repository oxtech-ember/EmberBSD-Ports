#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted harfbuzz Darwin CoreText compiler regression.
"""Evaluate the harfbuzz CoreText selection with real bmake for GCC and Clang.

The CoreText framework headers include CoreGraphics, which uses Apple blocks.
GCC cannot parse them, so a GCC build on Darwin must disable CoreText.
"""
import argparse
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--bmake', required=True, type=Path)
parser.add_argument('--pkgsrc', required=True, type=Path, help='a pkgsrc tree with mk/')
parser.add_argument('--work-parent', required=True, type=Path)
a = parser.parse_args()
recipe = Path(__file__).resolve().parents[1]

if platform.system() != 'Darwin':
    print('SKIP: the CoreText selection exists only on Darwin')
    sys.exit(0)

with tempfile.TemporaryDirectory(prefix='harfbuzz-coretext-', dir=a.work_parent) as temporary:
    root = Path(temporary)
    # Overlay only this recipe on the real tree; its includes stay real.
    source = a.pkgsrc.resolve()
    for entry in source.iterdir():
        if entry.name != 'fonts':
            (root / entry.name).symlink_to(entry)
    (root / 'fonts').mkdir()
    for entry in (source / 'fonts').iterdir():
        if entry.name != 'harfbuzz':
            (root / 'fonts' / entry.name).symlink_to(entry)
    package = root / 'fonts/harfbuzz'
    shutil.copytree(recipe, package, ignore=shutil.ignore_patterns('tests'))

    def evaluate(compiler):
        environment = {'PATH': os.environ.get('PATH', '/usr/bin:/bin'),
                       'HOME': os.environ.get('HOME', '/')}
        done = subprocess.run([str(a.bmake), '-r', 'MAKECONF=/dev/null',
                               f'PKGSRC_COMPILER={compiler}', f'CC={compiler.split()[-1]}',
                               '-V', '${MESON_ARGS:M-Dcoretext=*}|${PLIST.coretext}'],
                              cwd=package, env=environment, text=True,
                              capture_output=True, timeout=180)
        lines = done.stdout.strip().splitlines()
        assert done.returncode == 0 and lines, done.stdout + done.stderr
        return lines[-1]

    assert evaluate('gcc') == '-Dcoretext=disabled|', evaluate('gcc')
    assert evaluate('ccache gcc') == '-Dcoretext=disabled|'
    assert evaluate('clang') == '-Dcoretext=enabled|yes', evaluate('clang')
print('PASS: 3 harfbuzz Darwin CoreText compiler evaluations with real bmake')
