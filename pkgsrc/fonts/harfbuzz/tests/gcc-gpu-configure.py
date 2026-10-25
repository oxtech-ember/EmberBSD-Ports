#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted harfbuzz Darwin GPU demo regression.
"""Configure harfbuzz with GCC on Darwin and keep the GPU library.

harfbuzz 15 requires Objective-C++ on Darwin whenever the GPU library is
enabled, although only the hb-gpu demo (demo-metal.mm) needs it. GCC
builds have no Objective-C++, so meson stopped with "Unknown compiler(s)".
This test overlays this recipe on a real exported tree and runs its
configure phase with an accepted GCC MAKECONF. Meson must succeed and
still build libharfbuzz-gpu.
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
parser.add_argument('--pkgsrc', required=True, type=Path, help='an exported pkgsrc tree')
parser.add_argument('--makeconf', required=True, type=Path, help='a MAKECONF that selects GCC')
parser.add_argument('--work-parent', required=True, type=Path)
parser.add_argument('--make-var', action='append', default=[],
                    help='NAME=VALUE for bmake, such as EMBERBSD_DARWIN_BOOTSTRAP=yes')
a = parser.parse_args()
recipe = Path(__file__).resolve().parents[1]

if platform.system() != 'Darwin':
    print('SKIP: the Objective-C++ requirement exists only on Darwin')
    sys.exit(0)

with tempfile.TemporaryDirectory(prefix='harfbuzz-gpu-', dir=os.path.realpath(a.work_parent)) as temporary:
    root = Path(temporary) / 'pkgsrc'
    root.mkdir()
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
    make = [str(a.bmake), '-C', str(package), f'MAKECONF={a.makeconf}',
            f'WRKOBJDIR={temporary}/obj', *a.make_var]
    environment = {'PATH': '/usr/bin:/bin', 'HOME': os.environ.get('HOME', '/')}

    def show(name):
        done = subprocess.run(make + ['show-var', 'VARNAME=' + name], env=environment,
                              capture_output=True, text=True)
        assert done.returncode == 0, done.stdout + done.stderr
        return done.stdout.strip()

    compiler = show('PKGSRC_COMPILER').split()
    assert compiler and compiler[-1] == 'gcc', f'the MAKECONF selects {compiler}, not GCC'
    done = subprocess.run(make + ['configure'], env=environment, capture_output=True, text=True)
    output = done.stdout + done.stderr
    assert done.returncode == 0, output[-3000:]
    ninja = Path(show('WRKSRC'), 'output/build.ninja').read_text()
    assert 'libharfbuzz-gpu' in ninja, 'the GPU library is no longer built'
print('PASS: harfbuzz configures with GCC on Darwin and keeps libharfbuzz-gpu')
