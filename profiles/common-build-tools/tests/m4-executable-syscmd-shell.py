#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Run syscmd and esyscmd through a relocated @executable_path M4 shell.

Build M4 with --with-syscmd-shell=@executable_path/NAME first. The test
copies it into a new prefix whose path has a space and puts the shell beside
it. It checks absolute, PATH, symlink and relative invocations, real exit
statuses, and that a missing shell or executable fails without a fallback.
"""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--m4', type=Path, required=True)
parser.add_argument('--shell', type=Path, required=True)
parser.add_argument('--shell-name', default='mksh')
args = parser.parse_args()
fixture = (HERE / 'm4-syscmd-shell.m4').read_text()
expected = (HERE / 'm4-syscmd-shell.stdout').read_text()
probe = 'changequote([,])dnl\nesyscmd([test -n "$KSH_VERSION" && echo ksh])dnl\n'

with tempfile.TemporaryDirectory(prefix='ember-m4-relative-') as tmp:
    root = Path(tmp).resolve()
    bindir = root / 'installed space' / 'bin'
    bindir.mkdir(parents=True)
    binary = bindir / 'gm4'
    shell = bindir / args.shell_name
    shutil.copy2(args.m4, binary)
    shutil.copy2(args.shell, shell)
    other = root / 'other'
    other.mkdir()
    alias = other / 'm4'
    alias.symlink_to(binary)
    # No shell or m4 is reachable through PATH except the selected entry.
    env = dict(os.environ, PATH=str(bindir), SHELL='/unusable/environment-shell')

    def run(argv, *, environment=env, cwd=root, executable=None, text=fixture):
        return subprocess.run(argv, input=text, cwd=cwd, env=environment,
                              executable=executable, text=True,
                              capture_output=True)

    def check(argv, **kwargs):
        for text, want in ((fixture, expected), (probe, 'ksh\n')):
            result = run(argv, text=text, **kwargs)
            if result.returncode or result.stdout != want or result.stderr:
                raise AssertionError((argv, result.returncode, result.stdout,
                                      result.stderr))

    check([str(binary)])
    check(['gm4'])
    check([str(alias)])
    check(['m4'], environment=dict(env, PATH=str(other)))
    check(['../installed space/bin/gm4'], cwd=other)
    check(['gm4'], cwd=other, environment=dict(env, PATH='../installed space/bin'))

    # An unresolvable m4 executable is fatal, but only when a command runs.
    lost = dict(env, PATH=str(root / 'empty'))
    version = run(['not-installed-m4', '--version'], environment=lost,
                  executable=str(binary), text='')
    if version.returncode:
        raise AssertionError(('version without syscmd', version.stderr))
    unresolved = run(['not-installed-m4'], environment=lost, executable=str(binary))
    if (unresolved.returncode == 0 or 'cannot resolve' not in unresolved.stderr
            or 'm4-syscmd' in unresolved.stdout):
        raise AssertionError(('unresolved executable', unresolved.returncode,
                              unresolved.stdout, unresolved.stderr))

    # A missing relocated provider must not fall back to the producer or
    # system shell.
    shell.rename(shell.with_suffix('.saved'))
    missing = run([str(binary)])
    # Upstream reports a failed command as a warning and sysval 127.
    if ('cannot run command' not in missing.stderr or 'm4-syscmd' in missing.stdout
            or missing.stdout.splitlines()[:1] != ['127']):
        raise AssertionError(('missing provider', missing.returncode,
                              missing.stdout, missing.stderr))
print('M4 relocated syscmd/esyscmd, symlinks, PATH, relative and failures: PASS')
