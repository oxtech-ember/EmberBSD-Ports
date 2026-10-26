#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted). Exercises Perl's actual search-path fragments.
"""Verify Darwin Perl Configure and the generated pkgsrc callback search paths.

usage: perl-darwin-search-paths.py CONFIGURE POLICY MAKEFILE SHELL UTILITY_BIN WORK

The test runs the actual Configure include-search fragment, the complete
Policy.sh generator, and its generated callback. It does not build Perl.
"""
import json
import os
from pathlib import Path
import re
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
    require(policy.count('# MakeMaker uses lddlflags to link XS modules') == 1,
            'The canonical Perl Policy.sh must own exactly one XS cleanup block')
    start = configure.index('case "$mips_type" in\n', configure.index('locincpth='))
    end = configure.index('\ninctest=', start)
    include_fragment = configure[start:end]

    work.mkdir(mode=0o700)
    prefix = work / 'selected-prefix'
    (prefix / 'include').mkdir(parents=True)
    (prefix / 'lib').mkdir()
    values = dict(MACHINE_ARCH='arm64', LOWER_OPSYS='darwin', OBJECT_FMT='Mach-O',
                  CFLAGS='-O2', LDFLAGS='-Wl,generation-time-only', LOCALBASE=str(prefix),
                  TOOLS_SED=str(utility_bin / 'sed'))
    substituted = re.sub(r'@([A-Z0-9_]+)@', lambda m: values.get(m[1], ''), policy)
    # Keep the actual here-document untouched. Removing its quoting is the
    # precise defect this regression must distinguish from callback execution.
    start = substituted.index('# MakeMaker uses lddlflags to link XS modules')
    end = substituted.index('\n# Strip gdbm from libswanted', start)
    block = substituted[start:end]
    require(block.count('\\`') == 2, 'XS callback substitution must be deferred by Policy.sh')
    mutated = substituted[:start] + block.replace('\\`', '`') + substituted[end:]
    results = []
    for label, source in (('selected', substituted), ('unescaped-backticks', mutated)):
        case = work / label
        (case / 'UU').mkdir(parents=True)
        (case / 'Policy.sh').write_text(source)
        script = case / 'search-paths.sh'
        script.write_text(
            'set -e\ntest=' + shlex.quote(str(utility_bin / 'test')) + '\n'
            'mips_type=\nlocincpth=' + shlex.quote(str(prefix / 'include')) + '\n'
            'usrinc=/sdk/usr/include\ndflt=-O2\n' + include_fragment + '\n'
            'case "$dflt" in *"/usr/local/include"*) exit 81;; esac\n'
            'case "$dflt" in *"' + str(prefix / 'include') + '"*) ;; *) exit 82;; esac\n'
            'lddlflags=-Wl,generation-time-only\n. ./Policy.sh\n'
            '# Configure calls pkgsrc.cbu after hints have supplied these flags.\n'
            'ldflags="-L/usr/local/lib -L' + str(prefix / 'lib') + '"\n'
            'lddlflags="-bundle -L/usr/local/lib -L' + str(prefix / 'lib') + '"\n'
            '. ./UU/pkgsrc.cbu\n'
            'case "$lddlflags" in *"generation-time-only"*) exit 85;; esac\n'
            'case "$ldflags $lddlflags" in *"/usr/local/lib"*) exit 83;; esac\n'
            'case "$lddlflags" in *"' + str(prefix / 'lib') + '"*) ;; *) exit 84;; esac\n')
        result = subprocess.run([str(shell), str(script)], cwd=case,
                                env={'PATH': str(utility_bin), 'LC_ALL': 'C',
                                     'TZ': 'UTC', 'TMPDIR': str(work)},
                                capture_output=True, timeout=60)
        record = dict(case=label, argv=[str(shell), str(script)], exit=result.returncode,
                      stdout=result.stdout.decode(errors='replace'),
                      stderr=result.stderr.decode(errors='replace'))
        results.append(record)
        (work / 'result.json').write_text(json.dumps(results, indent=2) + '\n')
        expected = 0 if label == 'selected' else 85
        require(result.returncode == expected and result.stderr == b'',
                'Policy generation/callback result differs; inspect result.json')
    print(json.dumps(dict(status='PASS', scope='Actual Configure search, Policy.sh generation and callback; raw-backtick mutation fails; no Perl build')))


if __name__ == '__main__':
    main()
