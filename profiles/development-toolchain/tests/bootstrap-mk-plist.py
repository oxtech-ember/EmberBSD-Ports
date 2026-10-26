#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Check that ordinary bootstrap excludes the optional builtin helper."""

import argparse
from pathlib import Path
import shlex
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pkgsrc', type=Path, required=True)
    parser.add_argument('--make', type=Path, required=True)
    parser.add_argument('--makeconf', type=Path, required=True)
    args = parser.parse_args()
    variables = ('EMBERBSD_DARWIN_BOOTSTRAP', 'EMBERBSD_NETBSD_BOOTSTRAP',
                 'PLIST_SUBST', 'INSTALLATION_DIRS')
    command = [str(args.make.resolve(strict=True)),
               'MAKECONF=' + str(args.makeconf.resolve(strict=True))]
    for name in variables:
        command.extend(('-V', '${' + name + '}'))
    result = subprocess.run(command, cwd=args.pkgsrc / 'pkgtools/bootstrap-mk-files',
                            text=True, stdout=subprocess.PIPE, check=True)
    values = dict(zip(variables, result.stdout.splitlines(), strict=True))
    assert all(values[name] != 'yes' for name in variables[:2]), 'Select an ordinary bootstrap configuration'
    substitutions = dict(item.split('=', 1) for item in shlex.split(values['PLIST_SUBST']))
    assert substitutions.get('PLIST.builtin') == '@comment ', 'Optional helper remains an unresolved PLIST entry'
    assert 'libexec' not in shlex.split(values['INSTALLATION_DIRS']), 'Ordinary bootstrap must not install the helper'
    print('PASS ordinary bootstrap PLIST omits the optional builtin helper')


if __name__ == '__main__':
    main()
