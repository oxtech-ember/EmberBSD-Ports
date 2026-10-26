#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted). Exercises Perl's actual search-path fragments.
"""Verify Darwin Perl Configure starts and ends with selected prefix paths.

usage: perl-darwin-search-paths.py CONFIGURE POLICY MAKEFILE SHELL UTILITY_BIN WORK

The test runs the actual Perl Configure include-search fragment and the
Policy.sh callback fragment. It does not build or qualify Perl.
"""
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys


def require(value, message):
    if not value:
        raise AssertionError(message)


def main():
    if len(sys.argv) != 7:
        raise SystemExit(__doc__)
    configure_path, policy_path, makefile_path = map(Path, sys.argv[1:4])
    shell, utility_bin = Path(sys.argv[4]), Path(sys.argv[5])
    work = Path(sys.argv[6])
    require(all(p.is_absolute() and p.is_file() for p in
                (configure_path, policy_path, makefile_path, shell)),
            'Use exact absolute Perl source and selected shell paths')
    require(utility_bin.is_absolute() and utility_bin.is_dir(),
            'Use the selected native utility directory')
    require(work.is_absolute() and not os.path.lexists(work),
            'Use a fresh absolute work directory')

    configure = configure_path.read_text()
    policy = policy_path.read_text()
    makefile = makefile_path.read_text()
    for flag in ('-Dlocincpth=${LOCALBASE:Q}/include',
                 '-Dloclibpth=${LOCALBASE:Q}/lib'):
        require(flag in makefile, 'Perl Configure does not receive selected search root: ' + flag)

    start = configure.index('case "$mips_type" in\n', configure.index('locincpth='))
    end = configure.index('\ninctest=', start)
    include_fragment = configure[start:end]
    start = policy.index('# Strip /usr/local/lib... from ldflags\n')
    end = policy.index('\n# Strip gdbm from libswanted', start)
    policy_fragment = policy[start:end].replace('\\$', '$').replace('\\`', '`')
    require('lddlflags' in policy_fragment,
            'Policy.sh does not clean the Perl module linker flags')

    work.mkdir(mode=0o700)
    prefix = work / 'selected-prefix'
    (prefix / 'include').mkdir(parents=True)
    (prefix / 'lib').mkdir()
    script = work / 'search-paths.sh'
    script.write_text(
        'set -e\n'
        'mips_type=\nlocincpth=' + shlex.quote(str(prefix / 'include')) + '\n'
        'usrinc=/sdk/usr/include\ndflt=-O2\ntest=/bin/test\n' +
        include_fragment + '\n'
        'case "$dflt" in *"/usr/local/include"*) exit 81;; esac\n'
        'case "$dflt" in *"' + str(prefix / 'include') + '"*) ;; *) exit 82;; esac\n'
        'ldflags="-L/usr/local/lib -L' + str(prefix / 'lib') + '"\n'
        'lddlflags="-bundle -L/usr/local/lib -L' + str(prefix / 'lib') + '"\n' +
        policy_fragment + '\n'
        'case "$ldflags $lddlflags" in *"/usr/local/lib"*) exit 83;; esac\n'
        'case "$lddlflags" in *"' + str(prefix / 'lib') + '"*) ;; *) exit 84;; esac\n')
    result = subprocess.run([str(shell), str(script)], cwd=work,
                            env={'PATH': str(utility_bin), 'LC_ALL': 'C',
                                 'TZ': 'UTC', 'TMPDIR': str(work)},
                            capture_output=True, timeout=60)
    record = dict(argv=[str(shell), str(script)], exit=result.returncode,
                  stdout=result.stdout.decode(errors='replace'),
                  stderr=result.stderr.decode(errors='replace'))
    (work / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
    require(result.returncode == 0 and result.stderr == b'',
            'Actual Configure/Policy fragments retained host-local paths; inspect result.json')
    print(json.dumps(dict(status='PASS', scope='Actual Configure include search and Policy linker cleanup; no Perl build')))


if __name__ == '__main__':
    main()
