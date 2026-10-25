#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted), explicit optional Perl DTrace provider.
"""Evaluate real Perl options and bsd.options.mk with an accepted bmake tuple.

Run through the existing SDK owned-process interface. This source parser fixture
runs no Configure, compiler, DTrace executable, installed Perl, or target program.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import subprocess

NAMES = ('PKG_OPTIONS', 'PKG_OPTIONS.perl', 'CONFIGURE_ARGS', 'PKG_FAIL_REASON',
         'DTRACE', 'CFLAGS', 'PKGSRC_RUN_TEST', 'TEST_TARGET')


def require(value, message):
    if not value:
        raise AssertionError(message)


def check(row, selected=None, *, disabled=False, refused=False):
    options = [word for word in shlex.split(row['CONFIGURE_ARGS'])
               if word.startswith(('-Dusedtrace', '-Uusedtrace'))]
    expected = ['-Uusedtrace'] if disabled else ([] if refused else ['-Dusedtrace=' + selected])
    require(options == expected, 'The real options clause did not select exactly the declared DTrace path/state')
    require(bool(row['PKG_FAIL_REASON']) == refused, 'Unexpected DTrace provider refusal')
    require(('dtrace' in row['PKG_OPTIONS'].split()) == (not disabled), 'The canonical option resolver selected a different feature state')
    require(row['CFLAGS'] == '-Werror -fanalyzer' and row['PKGSRC_RUN_TEST'] == 'yes' and
            row['TEST_TARGET'] == 'check', 'Diagnostics, analyzer flags, or test policy changed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('options', 'bsd_options', 'profile', 'makeconf', 'shell', 'new_work'):
        parser.add_argument('--' + name.replace('_', '-'), type=Path, required=True)
    parser.add_argument('--make-arg', action='append', required=True)
    args = parser.parse_args()
    command, work = args.make_arg, args.new_work
    require(all(path.is_absolute() and path.is_file() for path in
                (args.options, args.bsd_options, args.profile, args.makeconf, args.shell)),
            'Use explicit source files and the selected shell')
    require(work.is_absolute() and work.resolve() == work and not os.path.lexists(work),
            'Use a new absolute work directory')
    require(len(command) == 5 and command[1] == '-m' and
            command[3] == 'SHELL=' + str(args.shell) and
            command[4] == 'MAKECONF=' + str(args.makeconf) and
            all(os.path.isabs(path) for path in (command[0], command[2])),
            'Supply the complete accepted bmake tuple')
    require(not any(char.isspace() for char in str(args.shell)), 'The .SHELL path must be one word')
    config = args.makeconf.read_text()
    require(not any(line.startswith(('_MAKE=', 'MAKE=', 'EMBERBSD_DARWIN_METADATA='))
                    for line in config.splitlines()), 'Use a full-format or phase-neutral MAKECONF')
    lines = config.splitlines(keepends=True)
    includes = [i for i, line in enumerate(lines) if re.fullmatch(
        r'\.include\s+"[^\"]*EMBERBSD-DARWIN-BOOTSTRAP-MK\.CONF"\s*\n?', line)]
    require(len(includes) == 1, 'Require the one real source profile include')
    lines[includes[0]] = '.include "' + str(args.profile) + '"\n'
    work.mkdir(mode=0o700)
    (work / 'empty-bin').mkdir()
    (work / 'lang/perl5').mkdir(parents=True)
    (work / 'mk/defaults').mkdir(parents=True)
    (work / 'lang/perl5/options.mk').write_bytes(args.options.read_bytes())
    (work / 'mk/bsd.options.mk').write_bytes(args.bsd_options.read_bytes())
    # Isolate unrelated platform discovery. Keep the complete real Perl options
    # and option resolver. These cases set no legacy or threaded option.
    (work / 'mk/bsd.prefs.mk').write_text('# Source fixture: host facts are explicit.\n')
    (work / 'mk/pthread.builtin.mk').write_text('USE_BUILTIN.pthread= no\n')
    (work / 'mk/defaults/obsolete.mk').write_text('# Source fixture: no legacy option variables.\n')
    makeconf = work / 'mk.conf'
    makeconf.write_text(''.join(lines))
    env = dict(PATH=str(work / 'empty-bin'), LC_ALL='C', TZ='UTC', TMPDIR=str(work))
    records = {}

    def query(name, values, *, profile=False):
        path = work / (name + '.mk')
        text = '.SHELL: name=sh path=' + str(args.shell) + ' hasErrCtl=no check="set -e" ignore="set +e" echoFlag=v errFlag=e\n'
        if profile:
            text += '.include "' + str(makeconf) + '"\nPKGPATH=lang/perl5\nBSD_PKG_MK=1\n'
            text += ('.include "' + str(makeconf) + '"\n') * 2
        text += '.include "' + str(work / 'lang/perl5/options.mk') + '"\n'
        path.write_text(text)
        argv = [*command[:4], 'MAKECONF=' + str(makeconf), '-r', '-f', str(path),
                'OPSYS=Darwin', 'OPSYS_VERSION=260000', 'MACHINE_PLATFORM=Darwin-aarch64',
                'DLOPEN_REQUIRE_PTHREADS=no', 'OBJECT_FMT=Mach-O', 'CFLAGS=-Werror -fanalyzer',
                'PKGSRC_RUN_TEST=yes', 'TEST_TARGET=check', *values,
                *[word for key in NAMES for word in ('-V', key + '=${' + key + '}')]]
        result = subprocess.run(argv, cwd=work, env=env, capture_output=True, timeout=60)
        (work / (name + '.stdout')).write_bytes(result.stdout)
        (work / (name + '.stderr')).write_bytes(result.stderr)
        record = dict(argv=argv, actual_exit=result.returncode)
        records[name] = record
        (work / 'observations.json').write_text(json.dumps(records, indent=2) + '\n')
        require(result.returncode == 0 and result.stderr == b'', 'Parser failure; inspect ' + name)
        rows = result.stdout.decode().splitlines()
        require(len(rows) == len(NAMES) and all(row.startswith(key + '=') for key, row in zip(NAMES, rows)),
                'Unexpected named query framing')
        row = dict((key, value.removeprefix(key + '=')) for key, value in zip(NAMES, rows))
        record['values'] = row
        return row

    selected = '/selected/sdk/bin/dtrace'
    check(query('selected', ['DTRACE=' + selected]), selected)
    for name, values in [('unset', []), ('empty', ['DTRACE=']),
                         ('relative', ['DTRACE=bin/dtrace']),
                         ('space', ['DTRACE=/selected/sdk with space/bin/dtrace'])]:
        check(query(name, values), refused=True)
    check(query('disabled', ['PKG_OPTIONS.perl=-dtrace']), disabled=True)
    check(query('cross-selected', ['OPSYS=NetBSD', 'USE_CROSS_COMPILE=yes',
        'PKG_OPTIONS.perl=dtrace', 'DTRACE=' + selected]), selected)
    check(query('cross-unset', ['OPSYS=NetBSD', 'USE_CROSS_COMPILE=yes',
        'PKG_OPTIONS.perl=dtrace']), refused=True)
    check(query('other-platform-default', ['OPSYS=NetBSD', 'USE_CROSS_COMPILE=yes']), disabled=True)
    for mode in ('yes', 'no', 'default'):
        values = ['EMBERBSD_DARWIN_BOOTSTRAP=yes']
        if mode != 'default':
            values += ['EMBERBSD_DARWIN_METADATA=' + mode]
        row = query('profile-' + mode, values, profile=True)
        check(row, disabled=True)
        require(row['PKG_OPTIONS.perl'].split().count('-dtrace') == 1,
                'The profile must select the option once across three includes')
    (work / 'observations.json').write_text(json.dumps(records, indent=2) + '\n')
    print(json.dumps(dict(status='PASS', scope='Actual source parser cases only; no Perl/DTrace execution',
                          queries=len(records), observations=str(work / 'observations.json'))))


if __name__ == '__main__':
    main()
