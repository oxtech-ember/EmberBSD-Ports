#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted). Evaluates the prepared native-tool map.
"""Run the selected Darwin native-tool commands the way pkgsrc wrappers do.

usage: darwin-bootstrap-native-tools.py EXPORTED_PKGSRC BMAKE SHELL NEW_WORK

bmake evaluates the exported mk/tools/tools.Darwin.mk in bootstrap mode.
The selected shell then runs each tool command with a PATH whose only entry
is a decoy directory: a bare command name would resolve to the decoy, the
same way a pkgsrc tool wrapper finds itself again in .tools/bin.
The shell builtins run the way pkgsrc passes them to scripts such as
mk/extract/extract: as an environment value expanded unquoted, as ${TEST}.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

TOOLS = {'mkdir': '/bin/mkdir', 'gzip': '/usr/bin/gzip', 'gunzip': '/usr/bin/gunzip',
         'printf': '/usr/bin/printf'}
BUILTINS = {'[': ('-n value ]', 0, ''), 'echo': ('plain  value', 0, 'plain value\n'),
            'false': ('', 1, ''), 'test': ('-n ""', 1, ''), 'true': ('', 0, '')}


def require(value, message):
    if not value:
        raise AssertionError(message)


def evaluate(exported, bmake, shell, work, names):
    work.mkdir(parents=True)
    lines = ['EMBERBSD_DARWIN_BOOTSTRAP= yes', f'EMBERBSD_DARWIN_BUILTIN_SHELL= {shell}',
             'EMBERBSD_DARWIN_NATIVE_TOOLS= ' + ' '.join(sorted(TOOLS))]
    lines += [f'EMBERBSD_DARWIN_TOOL.{name}= {path}' for name, path in sorted(TOOLS.items())]
    lines += [f'.include "{exported}/mk/tools/tools.Darwin.mk"', 'all:']
    for name in names:
        lines.append(f'\t@echo ${{TOOLS_PLATFORM.{name}:Q}}')
    (work / 'Makefile').write_text('\n'.join(lines) + '\n')
    out = subprocess.run([bmake, '-C', str(work), '-f', 'Makefile', 'all'], check=True,
                         capture_output=True, text=True, env={'PATH': '/usr/bin:/bin'}).stdout
    return dict(zip(names, out.splitlines()))


def main():
    if len(sys.argv) != 5:
        raise SystemExit(__doc__)
    exported, bmake, shell, work = sys.argv[1], sys.argv[2], sys.argv[3], Path(sys.argv[4])
    require(not work.exists(), 'NEW_WORK must not exist')
    names = ['mkdir', 'gzip', 'gunzip', 'printf'] + sorted(BUILTINS)
    tools = evaluate(exported, bmake, shell, work / 'eval', names)
    decoy = work / 'decoy'
    decoy.mkdir()
    for name in names:
        stub = decoy / name
        stub.write_text('#!/bin/sh\necho "decoy $0" >&2\nexit 97\n')
        stub.chmod(0o755)
    env = {'PATH': str(decoy), 'GZIP': ''}
    run = lambda script: subprocess.run([shell, '-c', script], env=env, cwd=work,
                                        capture_output=True, text=True)
    nested = work / 'a' / 'b' / 'c'
    result = run(f'{tools["mkdir"]} {nested} && {tools["mkdir"]} {nested}')
    require(result.returncode == 0 and nested.is_dir(),
            f'mkdir is not idempotent and recursive: {tools["mkdir"]!r} {result.stderr.strip()}')
    require(tools['printf'] == TOOLS['printf'],
            f'A tool without standard arguments is not its exact path: {tools["printf"]!r}')
    # pkgsrc scripts run some tools quoted, for example "${AWK}".
    result = run(f'"{tools["printf"]}" %s ok')
    require(result.returncode == 0 and result.stdout == 'ok',
            f'printf does not run without a shell builtin: {tools["printf"]!r} {result.stderr.strip()}')
    for name, (args, status, output) in BUILTINS.items():
        # mk/extract/extract.mk passes TEST=${TOOLS_TEST:Q}; the script runs ${TEST}.
        result = subprocess.run([shell, '-c', f'${{TOOL}} {args}'], env=dict(env, TOOL=tools[name]),
                                cwd=work, capture_output=True, text=True)
        require((result.returncode, result.stdout, result.stderr) == (status, output, ''),
                f'{name} does not run from an unquoted environment value: {tools[name]!r} '
                f'{result.returncode} {result.stdout!r} {result.stderr.strip()!r}')
    data = work / 'data'
    data.write_text('payload\n')
    result = run(f'{tools["gzip"]} {data} && {tools["gzip"]} -dc {data}.gz && '
                 f'{tools["gunzip"]} {data}.gz && test -f {data}')
    require(result.returncode == 0 and result.stdout == 'payload\n',
            f'gzip/gunzip commands failed: {result.stderr.strip()}')
    print(json.dumps({'shell': shell, 'tools': tools, 'result': 'PASS'}, sort_keys=True))


if __name__ == '__main__':
    main()
