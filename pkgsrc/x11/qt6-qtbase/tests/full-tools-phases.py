#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check the Qt provider guard at source and build phases with real bmake."""
import argparse
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('--bmake', required=True)
args = parser.parse_args()
guard = Path(__file__).resolve().parents[1] / 'full-tools-required.mk'
with tempfile.TemporaryDirectory(prefix='qt-full-tools-phase-') as name:
    work = Path(name)
    (work / 'Makefile').write_text('''FAIL_MSG= echo ERROR:; false
.include "''' + str(guard) + '''"
.include "''' + str(guard) + '''"
all:
\t@echo default-ok
show:
\t@echo show-ok
fetch:
\t@echo fetch-ok
pre-configure:
\t@echo configure-ok
pre-build:
\t@echo build-ok
''')
    for label, options, refuse in (
        ('native-host-tools', ['PKG_BUILD_OPTIONS.qt6-qtbase=host-tools'], True),
        ('native-full', ['PKG_BUILD_OPTIONS.qt6-qtbase=dbus'], False),
        ('cross', ['PKG_BUILD_OPTIONS.qt6-qtbase=host-tools', 'USE_CROSS_COMPILE=yes'], False),
    ):
        base = [args.bmake, '-r', '-f', str(work / 'Makefile'), *options]
        for goal, expected in (('default', 'default-ok'), ('show', 'show-ok'),
                               ('fetch', 'fetch-ok'), ('pre-configure', 'configure-ok'),
                               ('pre-build', 'build-ok')):
            result = subprocess.run(base + ([] if goal == 'default' else [goal]),
                                    cwd=work, text=True, capture_output=True)
            blocked = refuse and goal in ('pre-configure', 'pre-build')
            if blocked:
                assert result.returncode != 0 and 'requires full qt6-qtbase' in result.stdout, (label, goal, result)
            else:
                assert result.returncode == 0 and expected in result.stdout, (label, goal, result)
        result = subprocess.run(base + ['-V', 'PKG_FAIL_REASON'], cwd=work, text=True, capture_output=True)
        assert result.returncode == 0 and not result.stdout.strip(), (label, result)
    print('Qt full-tools source and build phases PASS')
