#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; actual-source sanitizer regressions.
set -eu
[ "$#" -eq 2 ] || { echo 'Usage: source-safety.sh SOURCE NEW_WORK' >&2; exit 2; }
: "${CXX:?Select an absolute native GCC16 C++ compiler}"
: "${PY:?Select an absolute Python interpreter}"
exec "$PY" - "$@" "$(dirname "$0")" <<'PY'
import os
from pathlib import Path
import shlex
import subprocess
import sys
source, work, tests = map(Path, sys.argv[1:])
compiler = os.environ['CXX']
if not Path(compiler).is_absolute() or not subprocess.check_output([compiler, '-dumpfullversion'], text=True).startswith('16.'):
    raise SystemExit('Select native GCC16')
work.mkdir()
flags = ['-std=c++11', '-O1', '-g', '-fsanitize=address,undefined,pointer-subtract',
         '-fno-sanitize-recover=all', '-fno-omit-frame-pointer']
flags += shlex.split(os.environ.get('HOST_CPPFLAGS', ''))
for directory in ['Marine', 'Utilities', 'JSON', 'Library', 'Application']:
    flags += ['-I' + str(source / 'Source' / directory)]
for name, extra in [('message-bounds', []), ('json-error', ['JSON/Parser.cpp', 'JSON/JSON.cpp',
                                                          'JSON/Keys.cpp', 'Utilities/Convert.cpp'])]:
    binary = work / name
    command = [compiler] + flags + [str(tests / (name + '.cpp'))]
    command += [str(source / 'Source' / item) for item in extra] + ['-o', str(binary)]
    with (work / (name + '-build.log')).open('wb') as output:
        subprocess.run(command, stdout=output, stderr=subprocess.STDOUT, check=True)
    with (work / (name + '-run.log')).open('wb') as output:
        subprocess.run([str(binary)], stdout=output, stderr=subprocess.STDOUT, check=True, timeout=30)
    print('PASS actual-source sanitizer regression: ' + name)
PY
