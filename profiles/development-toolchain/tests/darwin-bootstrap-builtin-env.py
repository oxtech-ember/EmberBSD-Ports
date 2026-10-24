#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted). Evaluates the policy with an accepted MAKECONF.
"""Check the builtin tool values that pkgsrc passes to its scripts.

usage: darwin-bootstrap-builtin-env.py EXPORTED_PKGSRC BMAKE MAKECONF WORK

pkgsrc passes TOOLS_ECHO, TOOLS_TEST, TOOLS_TRUE and TOOLS_FALSE to scripts
such as mk/extract/extract in the environment (ECHO=${TOOLS_ECHO:Q}), and the
scripts run them unquoted with ${SH}: `${TEST} $# -gt 0`. Each value must run
the selected shell's builtin there, even with decoy commands first in PATH.
"""
import json
import subprocess
import sys
from pathlib import Path

CASES = {
    'TOOLS_ECHO': [('plain  value', 0, 'plain value\n')],
    'TOOLS_FALSE': [('', 1, '')],
    'TOOLS_TEST': [('3 -gt 0', 0, ''), ('-n ""', 1, '')],
    'TOOLS_TRUE': [('', 0, '')],
}


def require(value, message):
    if not value:
        raise AssertionError(message)


def main():
    if len(sys.argv) != 5:
        raise SystemExit(__doc__)
    exported, bmake, makeconf, work = Path(sys.argv[1]), sys.argv[2], sys.argv[3], Path(sys.argv[4])
    names = ['SH'] + sorted(CASES)
    out = subprocess.run([bmake, '-C', str(exported / 'devel/libffi'), 'EMBERBSD_DARWIN_BOOTSTRAP=yes',
                          f'MAKECONF={makeconf}', 'show-vars', f'VARNAMES={" ".join(names)}'],
                         check=True, capture_output=True, text=True,
                         env={'PATH': '/usr/bin:/bin'}).stdout.splitlines()
    values = dict(zip(names, out))
    decoy = work / 'decoy'
    decoy.mkdir(parents=True)
    for name in ['[', 'echo', 'false', 'test', 'true']:
        stub = decoy / name
        stub.write_text('#!/bin/sh\necho decoy\nexit 99\n')
        stub.chmod(0o755)
    env = {'PATH': f'{decoy}:/usr/bin:/bin'}
    for name, cases in CASES.items():
        for args, status, output in cases:
            result = subprocess.run([values['SH'], '-c', f'${{TOOL}} {args}'], env=dict(env, TOOL=values[name]),
                                    cwd=work, capture_output=True, text=True)
            require((result.returncode, result.stdout, result.stderr) == (status, output, ''),
                    f'{name}={values[name]!r} does not run unquoted from the environment: '
                    f'{args!r} -> {result.returncode} {result.stdout!r} {result.stderr.strip()!r}')
    print(json.dumps({'result': 'PASS', 'sh': values['SH'], 'tools': {n: values[n] for n in CASES}},
                     sort_keys=True))


if __name__ == '__main__':
    main()
