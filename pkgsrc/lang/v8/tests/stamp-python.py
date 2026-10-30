#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check that lang/v8 runs stamp-source.py with the build host Python.

do-install ran ${PYTHONBIN}, the target LOCALBASE path. In a cross build
that path does not exist on the build host and install stopped.
"""
import argparse
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--pkgsrc', type=Path, required=True)
parser.add_argument('--makeconf', type=Path, required=True)
parser.add_argument('--bmake', required=True)
a = parser.parse_args()
makeconf = a.makeconf.resolve(strict=True)
r = subprocess.run([a.bmake, '-C', str(a.pkgsrc.resolve(strict=True) / 'lang/v8'),
                    'MAKECONF=' + str(makeconf),
                    '-V', '${V8_STAMP_PYTHON:U${PYTHONBIN}}'],
                   check=True, text=True, stdout=subprocess.PIPE,
                   stdin=subprocess.DEVNULL,
                   env=dict(os.environ, MAKECONF=str(makeconf)))
python = r.stdout.strip()
if not (os.path.isabs(python) and os.access(python, os.X_OK)):
    print('FAIL: stamp-source.py Python is not runnable on the build host: ' + repr(python))
    raise SystemExit(1)
print('PASS: stamp-source.py runs with ' + python)
