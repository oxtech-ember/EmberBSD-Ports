#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# EmberBSD (AI-assisted): execute production runner functions with host fixtures.
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys

if len(sys.argv) != 3:
    raise SystemExit('usage: mesa-package-loop.py RUNNER NEW_WORK')
runner = Path(sys.argv[1]).resolve(strict=True)
work = Path(sys.argv[2]).absolute()
work.mkdir()
text = runner.read_text()
def section(pattern):
    match = re.search(pattern, text, re.M | re.S)
    if not match:
        raise ValueError('cannot locate production runner section')
    return match.group()
loader = section(r'^check_loader\(\) \{.*?^\}')
render = section(r'^run_render\(\) \{.*?^\}')
loop = section(r'^failures=0\n.*\Z')
for name in ('bundle/bin', 'logs', 'tools'):
    (work / name).mkdir(parents=True, exist_ok=True)
def executable(path, body):
    path.write_text('#!/bin/sh\n' + body)
    path.chmod(0o755)
probe = work / 'bundle/bin/test-probe'
executable(probe, "printf 'executed actual fixture path\\n'\n")
(work / 'bundle/upstream-tests.tsv').write_text('fixture\ttest-probe\t30\n')
executable(work / 'tools/ldd', "printf 'libc.so.12 => /usr/lib/libc.so.12\\n'\n")
timeout = work / 'timeout'
executable(timeout, '[ "$1" = 30 ] || exit 91\nshift\n[ "$1" = ' + shlex.quote(str(probe)) + ' ] || exit 92\nexec "$@"\n')
setup = f'set -eu\nbundle={shlex.quote(str(work / "bundle"))}\nlogs={shlex.quote(str(work / "logs"))}\ntimeout={shlex.quote(str(timeout))}\n'
result = subprocess.run(['sh', '-c', setup + loader + '\n' + loop], env={**os.environ, 'PATH': str(work / 'tools') + ':' + os.environ['PATH']}, capture_output=True, text=True)
(work / 'loop.log').write_text('Host shell fixture only; no target runtime tested.\n' + result.stdout + result.stderr)
if result.returncode or 'executed actual fixture path' not in (work / 'logs/fixture.log').read_text():
    raise ValueError('production loop failed or lost executable name')
print('PASS: production loader and test loop')
render_timeout = work / 'render-timeout'
executable(render_timeout, '[ "$1" = 60 ] || exit 91\nshift\nexec "$@"\n')
executable(work / 'bundle/bin/mesa-render', '''printf '%s|%s|%s|%s|%s\\n' "${LIBGL_ALWAYS_SOFTWARE-unset}" "${GALLIUM_DRIVER-unset}" "${LD_PRELOAD-unset}" "$1" "$2"\n''')
for name, expected in (('llvmpipe', '1|llvmpipe|unset|surfaceless|llvmpipe'), ('other', 'unset|unset|unset|surfaceless|other')):
    shell = f'set -eu\nbundle={shlex.quote(str(work / "bundle"))}\ntimeout={shlex.quote(str(render_timeout))}\nrenderer={name}\n' + render + '\nrun_render\n'
    env = {**os.environ, 'LIBGL_ALWAYS_SOFTWARE': 'host', 'GALLIUM_DRIVER': 'host', 'LD_PRELOAD': 'host'}
    p = subprocess.run(['sh', '-c', shell], env=env, capture_output=True, text=True)
    if p.returncode or p.stdout.strip() != expected:
        raise ValueError(f'render environment mismatch: {p.stdout} {p.stderr}')
print('PASS: explicit llvmpipe and clean alternative renderer environment')
