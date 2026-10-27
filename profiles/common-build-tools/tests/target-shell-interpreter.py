#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check installed target shell scripts.
"""Check real bzip2 staging and build/runtime shell separation in pkgsrc."""
import argparse
import os
from pathlib import Path
import re
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pkgsrc', type=Path, required=True)
    parser.add_argument('--makeconf', type=Path, required=True)
    parser.add_argument('--host-prefix', type=Path, required=True)
    parser.add_argument('--stage', type=Path, required=True)
    args = parser.parse_args()
    prefix = args.host_prefix.resolve(strict=True)
    scripts = ('bzcmp', 'bzdiff', 'bzegrep', 'bzfgrep', 'bzgrep', 'bzless', 'bzmore')
    for name in scripts:
        with (args.stage / 'bin' / name).open('rb') as stream:
            header = stream.readline().rstrip(b'\r\n')
        if not re.fullmatch(rb'#![ \t]*/bin/sh[ \t]*', header):
            print(f'FAIL: {name}: staged interpreter must be the target /bin/sh', file=sys.stderr)
            return 1
    environment = dict(os.environ)
    for name in ('MAKEFLAGS', 'MFLAGS'):
        environment.pop(name, None)
    environment.update(PATH=f'{prefix}/bin:{prefix}/gnu/bin', LC_ALL='C')

    def query(variable, *options):
        command = [str(prefix / 'bin/bmake'), '-C', str(args.pkgsrc / 'archivers/bzip2'),
                   f'MAKECONF={args.makeconf}', f'TOOLS_PLATFORM.awk={prefix}/bin/nawk',
                   *options, 'show-var', f'VARNAME={variable}']
        result = subprocess.run(command, env=environment, capture_output=True,
                                text=True, timeout=120)
        if result.returncode or result.stderr.strip():
            raise RuntimeError(result.stderr or 'pkgsrc metadata query failed')
        return result.stdout.strip()

    build_shell = query('CONFIG_SHELL')
    if not Path(build_shell).resolve(strict=True).is_relative_to(prefix):
        raise RuntimeError('Build shell is outside the selected native prefix')
    if query('REPLACE.sys-sh.new') != '/bin/sh':
        raise RuntimeError('Cross replacement does not select the target base shell')
    if query('REPLACE.sys-sh.new', 'USE_CROSS_COMPILE=no') != build_shell:
        raise RuntimeError('Native interpreter policy changed')
    print('PASS: seven staged target scripts, selected native build shell, and unchanged native replacement')
    return 0


if __name__ == '__main__':
    sys.exit(main())
