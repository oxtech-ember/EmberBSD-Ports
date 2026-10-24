#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted). Evaluates the policy with an accepted MAKECONF.
"""Check that bare ar, nm, ranlib and strip reach the selected commands.

usage: darwin-bootstrap-binutils-tools.py EXPORTED_PKGSRC BMAKE MAKECONF

Configure scripts and Makefiles run these names from PATH. In bootstrap mode
PATH holds only the utility directory and the tools directory, so the policy
must create each tool there and point it at the selected command.
"""
import json
import subprocess
import sys
from pathlib import Path

TOOLS = ['ar', 'nm', 'ranlib', 'strip']


def require(value, message):
    if not value:
        raise AssertionError(message)


def main():
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    exported, bmake, makeconf = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    names = ['TOOLS_CREATE', 'TOOLS_NOOP'] + [f'TOOLS_PATH.{t}' for t in TOOLS] + \
        [f'EMBERBSD_GCC16_{t.upper()}' for t in TOOLS]
    out = subprocess.run([bmake, '-C', str(exported / 'pkgtools/digest'), 'EMBERBSD_DARWIN_BOOTSTRAP=yes',
                          f'MAKECONF={makeconf}', 'show-vars', f'VARNAMES={" ".join(names)}'],
                         check=True, capture_output=True, text=True,
                         env={'PATH': '/usr/bin:/bin'}).stdout.splitlines()
    values = dict(zip(names, out))
    created = values['TOOLS_CREATE'].split()
    result = {}
    for tool in TOOLS:
        path = values[f'TOOLS_PATH.{tool}']
        require(created.count(tool) == 1, f'{tool} is not created exactly once in the tools directory')
        require(tool not in values['TOOLS_NOOP'].split(), f'{tool} is also a no-op tool')
        require(path == values[f'EMBERBSD_GCC16_{tool.upper()}'] and path.startswith('/'),
                f'{tool} does not use the selected command: {path!r}')
        run = subprocess.run([path, '--version'], capture_output=True, text=True, env={'PATH': ''})
        require(run.returncode == 0, f'Selected {tool} does not run: {path}')
        result[tool] = path
    print(json.dumps({'tools': result, 'result': 'PASS'}, sort_keys=True))


if __name__ == '__main__':
    main()
