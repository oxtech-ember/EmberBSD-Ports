#!/usr/bin/env python3
# $NetBSD$
# Origin: EmberBSD (AI-assisted).
# Regression: installed psl-make-dafsa must run with its shebang interpreter.
#
# usage: psl-make-dafsa-runtime.py PREFIX
import os
import subprocess
import sys
import tempfile

if len(sys.argv) != 2:
    raise SystemExit('usage: psl-make-dafsa-runtime.py PREFIX')
prefix = os.path.abspath(sys.argv[1])
tool = os.path.join(prefix, 'bin/psl-make-dafsa')
if not os.path.isfile(tool):
    raise SystemExit(f'FAIL: missing {tool}')
with open(tool, 'r', encoding='utf-8') as handle:
    shebang = handle.readline().rstrip('\n')
if not shebang.startswith('#!'):
    raise SystemExit(f'FAIL: {tool} has no shebang')
interpreter = shebang[2:].split()[0]
# Prefer the package prefix interpreter when REPLACE_PYTHON rewrote it there.
if interpreter.startswith(prefix + os.sep) and not os.path.exists(interpreter):
    raise SystemExit(f'FAIL: shebang interpreter missing: {interpreter}')
if not os.path.exists(interpreter):
    raise SystemExit(f'FAIL: shebang interpreter missing: {interpreter}')

sample = 'com\n*.ck\n!www.ck\nblogspot.com\n'
with tempfile.TemporaryDirectory(prefix='psl-make-dafsa-') as tmp:
    source = os.path.join(tmp, 'list.dat')
    binary = os.path.join(tmp, 'list.dafsa')
    with open(source, 'w', encoding='utf-8') as handle:
        handle.write(sample)
    result = subprocess.run([tool, '--output-format=binary', source, binary],
                            capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        raise SystemExit('FAIL: psl-make-dafsa failed')
    if not os.path.isfile(binary) or os.path.getsize(binary) == 0:
        raise SystemExit('FAIL: psl-make-dafsa produced no binary output')
print('PASS: installed psl-make-dafsa runs with its runtime Python interpreter')
