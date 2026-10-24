#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Actual pkgsrc recipe selection checks.
import os
from pathlib import Path
import re
import subprocess
import sys
sys.dont_write_bytecode = True
from llvm_fixture import load_sdk
sdk, args = load_sdk()
if len(args) != 2:
    sys.exit('Use EXPORTED_PKGSRC NEW_OUTPUT')
tree, out = Path(args[0]).absolute(), Path(args[1]).absolute()
out.mkdir()
make = os.environ.get('BMAKE', 'bmake')
base = ['PKG_OPTIONS.clang=-tests', 'PKG_OPTIONS.lld=-tests'] + [k + '=' + os.environ[k] for k in ('PKG_INFO', 'PKG_ADMIN', 'PKG_DBDIR') if k in os.environ]
for package in ('lang/clang', 'devel/lld', 'devel/py-llvm-lit'):
    values = ['PKGNAME', 'PYTHONBIN', 'DEPENDS', 'CONFLICTS', 'PKG_FAIL_REASON']
    command = [make, '-C', str(tree / package), *base, 'PYTHON_VERSION_REQD=315']
    for name in values:
        command.extend(['-v', name])
    result = subprocess.run(command, capture_output=True, text=True)
    (out / (package.replace('/', '-') + '.txt')).write_text(result.stdout + result.stderr)
    lines = result.stdout.splitlines()
    assert result.returncode == 0 and len(lines) == len(values) and not lines[-1], result.stdout + result.stderr
    assert lines[1] == '/usr/pkg/bin/python3.15' and not re.search(r'python314|py314-', lines[2])
    if package == 'devel/py-llvm-lit':
        assert lines[0] == 'py315-llvm-lit-23.1.4nb1' and 'py[0-9]*-llvm-lit-[0-9]*' in lines[3].split()
    else:
        assert 'py315-llvm-lit>=23.1.4nb1:' in lines[2]
        if package == 'lang/clang':
            assert re.search(r'python315>=3\.15[^:]*:', lines[2])
    rejected = subprocess.run([make, '-C', str(tree / package), '-v', 'PKG_FAIL_REASON', *base, 'PYTHON_VERSION_REQD=314'], capture_output=True, text=True)
    (out / (package.replace('/', '-') + '-old.txt')).write_text(rejected.stdout + rejected.stderr)
    assert re.search(r'No valid Python version|[Ii]ncompatible|[Nn]ot.*support|[Nn]ot.*accept|requires Python|PYTHON_VERSION_REQD', rejected.stdout + rejected.stderr)
print('PASS: current selectors, explicit Clang runtime, lit provider conflict and old ABI rejection')
