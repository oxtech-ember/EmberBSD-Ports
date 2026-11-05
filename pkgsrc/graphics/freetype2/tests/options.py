#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check FreeType's optional LCD renderer and dynamic HarfBuzz policy."""
import argparse
import os
import shlex
from pathlib import Path
import shutil
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--bmake', type=Path, required=True)
p.add_argument('--pkgsrc', type=Path, required=True)
a = p.parse_args()
recipe = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='freetype-options-') as directory:
    root = Path(directory)
    for entry in a.pkgsrc.resolve().iterdir():
        if entry.name != 'graphics':
            (root / entry.name).symlink_to(entry)
    (root / 'graphics').mkdir()
    for entry in (a.pkgsrc / 'graphics').iterdir():
        if entry.name != 'freetype2':
            (root / 'graphics' / entry.name).symlink_to(entry.resolve())
    shutil.copytree(recipe, root / 'graphics/freetype2', ignore=shutil.ignore_patterns('tests'))
    def evaluate(option):
        cmd = [str(a.bmake), '-r', 'MAKECONF=/dev/null', 'PKGSRC_COMPILER=clang', 'CC=clang', 'LOCALBASE=' + str(a.bmake.resolve().parent.parent)]
        if option:
            cmd.append('PKG_OPTIONS.freetype2=' + option)
        cmd += ['-V', '${CONFIGURE_ARGS:M--with-harfbuzz=*}|${PKG_OPTIONS:Msubpixel}|${SUBST_SED.subpixel}']
        result = subprocess.run(cmd, cwd=root / 'graphics/freetype2', text=True, capture_output=True, env={'PATH': os.environ['PATH'], 'HOME': os.environ.get('HOME', '/')})
        assert result.returncode == 0, result.stdout + result.stderr
        return result.stdout.strip().splitlines()[-1]
    default = evaluate('')
    disabled = evaluate('-subpixel')
    assert '--with-harfbuzz=dynamic|subpixel|' in default, default
    sed_args = shlex.split(default.split('|', 2)[2])
    rendered = subprocess.run(['sed', *sed_args], input='/* #define FT_CONFIG_OPTION_SUBPIXEL_RENDERING */\n', text=True, capture_output=True, check=True).stdout
    assert rendered == '#define FT_CONFIG_OPTION_SUBPIXEL_RENDERING\n', rendered
    assert disabled == '--with-harfbuzz=dynamic||', disabled
print('PASS: dynamic HarfBuzz and selectable default-on LCD rendering')
