#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Run Ninja commands using its relocated executable-relative shell."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--ninja', type=Path, required=True)
parser.add_argument('--shell', type=Path, required=True)
parser.add_argument('--shell-name', choices=('mksh', 'pdksh'), default='mksh')
args = parser.parse_args()
with tempfile.TemporaryDirectory(prefix='ember-ninja-relative-') as tmp:
    root = Path(tmp).resolve()
    prefix = root / 'installed space'
    bindir = prefix / 'bin'
    bindir.mkdir(parents=True)
    binary = bindir / 'ninja'
    shell = bindir / args.shell_name
    shutil.copy2(args.ninja, binary)
    shutil.copy2(args.shell, shell)
    other = root / 'other'
    other.mkdir()
    alias = other / 'linked-ninja'
    alias.symlink_to(binary)
    project = root / 'project'
    project.mkdir()
    (project / 'build.ninja').write_text('''rule probe
  command = case "$$0" in */%s) echo "$$0" > $out;; *) exit 9;; esac
rule fail
  command = exit 7
build probe.out: probe
build failure: fail
default probe.out
''' % args.shell_name)
    env = dict(os.environ, PATH=str(bindir), SHELL='/unusable/environment-shell')

    def run(command, *, environment=env, cwd=project, extra=()):
        out = project / 'probe.out'
        if out.exists():
            out.unlink()
        result = subprocess.run(command + [*extra], cwd=cwd, env=environment,
                                text=True, capture_output=True)
        if result.returncode or not out.is_file() or out.read_text().strip() != str(shell):
            raise AssertionError((command, result.returncode, result.stdout, result.stderr))

    run([str(binary)])
    run(['ninja'])
    run([str(alias)])
    run(['linked-ninja'], environment=dict(env, PATH=str(other)))
    run(['../installed space/bin/ninja', '-C', str(project)], cwd=other)
    run(['ninja', '-C', str(project)], cwd=other,
        environment=dict(env, PATH='../installed space/bin'))
    failure = subprocess.run([str(binary), 'failure'], cwd=project, env=env,
                             text=True, capture_output=True)
    if failure.returncode == 0 or 'FAILED:' not in failure.stdout:
        raise AssertionError(('command failure', failure.returncode, failure.stdout))
    # A missing relocated provider cannot silently fall back to the producer
    # or system shell.
    shell.rename(shell.with_suffix('.saved'))
    (project / 'probe.out').unlink()
    missing = subprocess.run([str(binary)], cwd=project, env=env,
                             text=True, capture_output=True)
    if missing.returncode == 0 or 'posix_spawn' not in missing.stderr + missing.stdout:
        raise AssertionError(('missing provider', missing.returncode, missing.stderr))
print('Ninja relocated commands, symlinks, PATH, -C and failures: PASS')
