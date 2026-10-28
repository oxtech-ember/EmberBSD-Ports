#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Exercise ordinary editor and encoding operations with a selected host nvi."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--program', type=Path, required=True)
p.add_argument('--prefix', type=Path, required=True)
p.add_argument('--work-dir', type=Path, required=True)
p.add_argument('--locale', required=True, help='installed UTF-8 host locale')
a = p.parse_args()
env = dict(os.environ, TERM='xterm', LC_ALL=a.locale,
           PATH=str(a.prefix / 'bin') + ':' + str(a.prefix / 'gnu/bin'))
with tempfile.TemporaryDirectory(dir=a.work_dir) as tmp:
    root = Path(tmp)
    cases = [('latin', 'café', b'caf\xe9'),
             ('long', 'é' * 1400, b'\xe9' * 1400),
             ('fallback', 'prix €', b'prix \xe2\x82\xac')]
    for name, content, expected in cases:
        file = root / (name + '.txt')
        file.write_text('base\n')
        commands = 'set fileencoding=ISO-8859-1\n$a\n' + content + '\n.\nwq\n'
        result = subprocess.run([str(a.program), '-e', '-s', str(file)],
                                input=commands, text=True, capture_output=True,
                                env=env, timeout=20)
        if (result.returncode or file.read_bytes() != b'base\n' + expected + b'\n'
                or 'runtime error:' in result.stderr or 'AddressSanitizer' in result.stderr):
            raise AssertionError(name + ': ' + result.stdout + result.stderr)
    file = root / 'edit.txt'
    file.write_text('alpha\nbeta\n')
    result = subprocess.run([str(a.program), '-e', '-s', str(file)],
                            input='1s/alpha/first/\nwq\n', text=True,
                            capture_output=True, env=env, timeout=20)
    if (result.returncode or file.read_text() != 'first\nbeta\n'
            or 'BDB0635' in result.stdout + result.stderr
            or 'runtime error:' in result.stderr or 'AddressSanitizer' in result.stderr):
        raise AssertionError('normal edit: ' + result.stdout + result.stderr)
    file = root / 'readonly.txt'
    file.write_text('alpha\n')
    result = subprocess.run([str(a.program), '-e', '-s', '-R', str(file)],
                            input='1s/alpha/beta/\nw\nq!\n', text=True,
                            capture_output=True, env=env, timeout=20)
    if (result.returncode != 1 or file.read_text() != 'alpha\n'
            or 'Read-only file' not in result.stdout + result.stderr
            or 'runtime error:' in result.stderr or 'AddressSanitizer' in result.stderr):
        raise AssertionError('readonly: ' + result.stdout + result.stderr)
print('nvi ordinary edit and encoding: PASS')
