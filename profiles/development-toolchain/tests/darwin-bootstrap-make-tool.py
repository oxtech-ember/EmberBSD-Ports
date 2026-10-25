#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted). Evaluates the policy with an accepted MAKECONF.
"""Check the "make" tool that pkgsrc creates from MAKE_PROGRAM.

usage: darwin-bootstrap-make-tool.py EXPORTED_PKGSRC BMAKE MAKECONF WORK

After the make handoff the gmake command has a SHELL= argument. Recursive
builds run the created "make" tool, for example perl's cpan/Encode. Each
recipe here runs its tools phase in WORK, which must not exist. The created
tool must run the selected make with every argument of MAKE_PROGRAM.
Use a MAKECONF whose LOCALBASE contains the recipe dependencies.
"""
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

# A later recipe that uses gmake, and one that uses the Ports bmake.
RECIPES = {'lang/perl5': 'GNU Make', 'pkgtools/pkg_install': None}
NAMES = ('MAKE_PROGRAM', 'TOOLS_PATH.make', 'TOOLS_ARGS.make', 'WRKDIR')


def require(value, message):
    if not value:
        raise AssertionError(message)


def bmake(bmake_path, exported, makeconf, work, recipe, *args):
    return subprocess.run([bmake_path, '-C', str(exported / recipe), 'EMBERBSD_DARWIN_BOOTSTRAP=yes',
                           f'MAKECONF={makeconf}', f'WRKOBJDIR={work}', *args],
                          check=True, capture_output=True, text=True,
                          env={'PATH': '/usr/bin:/bin', 'HOME': os.environ.get('HOME', '/')}).stdout


def main():
    if len(sys.argv) != 5:
        raise SystemExit(__doc__)
    exported, bmake_path, makeconf = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    work = Path(os.path.realpath(sys.argv[4]))
    require(not work.exists(), f'{work} already exists')
    work.mkdir(parents=True)
    result = {}
    for recipe, banner in RECIPES.items():
        values = dict(zip(NAMES, bmake(bmake_path, exported, makeconf, work, recipe, 'show-vars',
                                       f'VARNAMES={" ".join(NAMES)}').splitlines()))
        program = shlex.split(values['MAKE_PROGRAM'])
        require(program and program == [values['TOOLS_PATH.make'], *shlex.split(values['TOOLS_ARGS.make'])],
                f'{recipe} splits {program} into {values["TOOLS_PATH.make"]!r} {values["TOOLS_ARGS.make"]!r}')
        bmake(bmake_path, exported, makeconf, work, recipe, 'tools')
        tool = Path(values['WRKDIR']) / '.tools/bin/make'
        require(os.path.isfile(tool) and os.access(tool, os.X_OK),
                f'{recipe} has no runnable make tool: {os.readlink(tool) if tool.is_symlink() else tool}')
        require(tool.is_symlink() == (len(program) == 1),
                f'{recipe} make tool is a {"symlink" if tool.is_symlink() else "wrapper"} for {program}')
        if banner:
            out = subprocess.run([str(tool), '--version'], capture_output=True, text=True,
                                 env={'PATH': '/usr/bin:/bin'})
            require(out.returncode == 0 and out.stdout.startswith(banner),
                    f'{recipe} make tool fails: {out.returncode} {out.stderr.strip()}')
        result[recipe] = {'program': program, 'tool': 'symlink' if tool.is_symlink() else 'wrapper'}
    print(json.dumps({'recipes': result, 'result': 'PASS'}, sort_keys=True))


if __name__ == '__main__':
    main()
