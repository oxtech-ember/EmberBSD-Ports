#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Exercise a bmake built with the executable-relative Ports defaults."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--bmake', type=Path, required=True)
parser.add_argument('--shell', type=Path, required=True)
args = parser.parse_args()
with tempfile.TemporaryDirectory(prefix='ember-bmake-relative-') as tmp:
    root = Path(tmp).resolve()
    prefix = root / 'installed'
    bindir, mk = prefix / 'bin', prefix / 'share/mk'
    bindir.mkdir(parents=True)
    mk.mkdir(parents=True)
    binary = bindir / 'bmake'
    shutil.copy2(args.bmake, binary)
    (bindir / 'mksh').symlink_to(args.shell.resolve())
    (mk / 'sys.mk').write_text('PROBE=installed\n')
    alternate = root / 'alternate'
    alternate.mkdir()
    (alternate / 'sys.mk').write_text('PROBE=alternate\n')
    other = root / 'other'
    other.mkdir()
    aliases = root / 'aliases'
    aliases.mkdir()
    (aliases / 'linked-make').symlink_to(binary)
    env = dict(os.environ, PATH=str(bindir))
    for name in ('MAKESYSPATH', 'MAKEFLAGS', 'MFLAGS'):
        env.pop(name, None)
    expected_shell = str(bindir / 'mksh')

    def check(command, *, environment=env, executable=None, expected='installed', shell=expected_shell):
        result = subprocess.run(command + ['-V', 'PROBE', '-V', '.SHELL'], cwd=other,
                                env=environment, executable=executable, text=True, capture_output=True)
        if result.returncode or result.stdout.splitlines() != [expected, shell]:
            raise AssertionError((command, result.returncode, result.stdout, result.stderr))

    check([str(binary)])
    recipe = root / 'recipe.mk'
    recipe.write_text("all:\n\t@case \"$$0\" in */mksh) echo recipe-ok;; *) exit 1;; esac\n")
    run = subprocess.run([str(binary), '-f', str(recipe), 'all'], cwd=other, env=env,
                         text=True, capture_output=True)
    if run.returncode or run.stdout.strip() != 'recipe-ok':
        raise AssertionError(('default shell recipe', run.returncode, run.stdout, run.stderr))
    check(['bmake'])
    (other / 'here-make').symlink_to(binary)
    check(['here-make'], environment=dict(env, PATH=':/nonexistent'))
    check(['../installed/bin/bmake', '-C', str(root)])
    check(['bmake', '-C', str(root)], environment=dict(env, PATH='../installed/bin'))
    check([str(aliases / 'linked-make')])
    env_alias = dict(env, PATH=str(aliases))
    check(['linked-make'], environment=env_alias)
    check(['bmake', '-C', str(other)])
    check([str(binary), '-m', str(alternate)], expected='alternate')
    check([str(binary)], environment=dict(env, MAKESYSPATH=str(alternate)), expected='alternate')
    override = root / 'override.mk'
    override.write_text('.SHELL: name=sh path=' + str(args.shell.resolve()) + '\n')
    check([str(binary), '-f', str(override)], shell=str(args.shell.resolve()))
    check(['no-such-make', '-m', str(alternate), '-f', str(override)],
          executable=str(binary), environment=dict(env, PATH=str(root / 'missing')),
          expected='alternate', shell=str(args.shell.resolve()))
    missing = subprocess.run(['no-such-make', '-V', 'PROBE'], executable=str(binary), cwd=other,
                             env=dict(env, PATH=str(root / 'missing')), text=True, capture_output=True)
    if missing.returncode == 0 or 'cannot resolve bmake executable' not in missing.stderr:
        raise AssertionError(('unresolved executable', missing.returncode, missing.stderr))
print('executable-relative defaults and explicit overrides: PASS')
