#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Source-only shell selector and argv checks.
"""Check the real recipe flag transport without compiling or running nawk."""
import argparse
import os
from pathlib import Path
import shlex
import subprocess


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--recipe', required=True, type=Path)
    cli.add_argument('--bmake', required=True, type=Path)
    cli.add_argument('--work', required=True, type=Path)
    args = cli.parse_args()
    if not all(path.is_absolute() for path in (args.recipe, args.bmake, args.work)):
        cli.error('Select absolute paths')
    args.work.mkdir()
    makefile = args.work / 'recipe.mk'
    # Evaluate the production selector and flags. Full pkgsrc includes remain
    # a separate package check; no replacement selector is used here.
    production = (args.recipe / 'Makefile').read_text().split('BUILD_TARGET=', 1)[0]
    makefile.write_text('CFLAGS= -O2\n' + production)
    env = dict(os.environ, MAKEFLAGS='', MAKECONF='/dev/null')
    command = [str(args.bmake), '-r', '-m', '/', '-f', str(makefile), 'CC=/selected/gcc16']

    def query(expression, shell):
        variables = [] if shell is None else ['NAWK_COMMAND_SHELL=' + shell]
        return subprocess.run(command + variables + ['-V', expression], env=env,
                              check=True, capture_output=True, text=True).stdout.strip()

    for shell in (None, '/selected/sdk/bin/sh', '/selected/sdk+1/bin/mksh'):
        assert not query('${PKG_FAIL_REASON}', shell)
        assignments = shlex.split(query('${MAKE_FLAGS}', shell))
        plan = subprocess.run([str(args.bmake), '-r', '-n', *assignments, 'a.out'],
                              cwd=args.recipe / 'files', env=env, check=True,
                              capture_output=True, text=True).stdout
        lines = [shlex.split(line) for line in plan.splitlines()]
        assert lines and all(line[0] == '/selected/gcc16' for line in lines)
        for argv in lines:
            selected = [word for word in argv if word.startswith('-DNAWK_COMMAND_SHELL=')]
            assert selected == ([] if shell is None else ['-DNAWK_COMMAND_SHELL="' + shell + '"'])
    for shell in ('', 'relative/sh', '/selected/bad shell', '/selected/sh;false', '/selected/"sh',
                  '/selected/sh ', '/selected/\tsh'):
        assert 'NAWK_COMMAND_SHELL must be an absolute shell path' in query('${PKG_FAIL_REASON}', shell)
    print('PASS: default and selected shell compiler argv; seven invalid paths rejected')
    print('SOURCE ONLY: no compiler, shell adapter or package execution')


if __name__ == '__main__':
    main()
