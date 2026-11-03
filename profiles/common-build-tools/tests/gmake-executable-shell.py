#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Run GNU make recipes using its relocated default shell."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--gmake', type=Path, required=True)
parser.add_argument('--shell', type=Path, required=True)
parser.add_argument('--shell-name', choices=('mksh', 'pdksh'), default='mksh')
args = parser.parse_args()
with tempfile.TemporaryDirectory(prefix='ember-gmake-relative-') as tmp:
    root = Path(tmp).resolve()
    prefix = root / 'installed space'
    bindir = prefix / 'bin'
    bindir.mkdir(parents=True)
    binary = bindir / 'gmake'
    shell = bindir / args.shell_name
    shutil.copy2(args.gmake, binary)
    shutil.copy2(args.shell, shell)
    gnu = prefix / 'gnu/bin'
    gnu.mkdir(parents=True)
    (gnu / 'make').symlink_to('../../bin/gmake')
    other = root / 'other'
    other.mkdir()
    alias = other / 'linked-make'
    alias.symlink_to(binary)
    env = dict(os.environ, PATH=str(bindir), SHELL='/unusable/environment-shell')
    for name in ('MAKEFLAGS', 'MFLAGS', 'GNUMAKEFLAGS', 'MAKELEVEL', 'MAKEFILES'):
        env.pop(name, None)
    recipe = root / 'probe.mk'
    recipe.write_text('''all:
	@echo '$(SHELL)'; case "$$0" in */mksh|*/pdksh) echo recipe-ok;; *) exit 9;; esac
recurse:
	@"$(MAKE)" --no-print-directory -f "$(lastword $(MAKEFILE_LIST))" all
oneshell:
	@set -e
	@echo one
	@echo two
.ONESHELL: oneshell
failure:
	@exit 7
''')

    def run(command, *, environment=env, target='all', expected=None, cwd=other, extra=()):
        result = subprocess.run(command + ['--no-print-directory', '-f', str(recipe), *extra, target],
                                cwd=cwd, env=environment, text=True, capture_output=True)
        wanted = expected if expected is not None else [str(shell), 'recipe-ok']
        if result.returncode or result.stdout.splitlines() != wanted:
            raise AssertionError((command, result.returncode, result.stdout, result.stderr))

    run([str(binary)])
    run(['gmake'])
    run([str(alias)])
    run(['linked-make'], environment=dict(env, PATH=':/nonexistent'))
    run(['linked-make'], environment=dict(env, PATH='/nonexistent:'))
    run(['../installed space/bin/gmake', '-C', str(root)])
    run(['gmake', '-C', str(root)], environment=dict(env, PATH='../installed space/bin'))
    run([str(gnu / 'make')])
    run([str(binary)], target='recurse')
    run([str(binary)], target='oneshell', expected=['one', 'two'])
    failure = subprocess.run([str(binary), '-f', str(recipe), 'failure'], cwd=other,
                             env=env, text=True, capture_output=True)
    if failure.returncode != 2 or 'Error 7' not in failure.stderr:
        raise AssertionError(('recipe failure', failure.returncode, failure.stderr))
    # A missing relocated provider cannot silently fall back to the producer
    # or system shell.  An explicit command-line SHELL still takes precedence.
    shell.rename(shell.with_suffix('.saved'))
    missing = subprocess.run([str(binary), '-f', str(recipe), 'all'], cwd=other,
                             env=env, text=True, capture_output=True)
    if missing.returncode == 0:
        raise AssertionError('missing provider unexpectedly succeeded')
    run([str(binary)], expected=[str(args.shell.resolve()), 'recipe-ok'],
        extra=['SHELL=' + str(args.shell.resolve())])
print('GNU make relocated recipes, recursion, symlinks, PATH, -C and overrides: PASS')
