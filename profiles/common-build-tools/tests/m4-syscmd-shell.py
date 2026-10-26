#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted), GNU M4 recipe/runtime shell selection.
"""Evaluate the real M4 recipe and Darwin profile with an accepted bmake tuple.

Run this source fixture through the existing SDK owned-process interface.
This fixture runs no configure, compiler, installed provider or target program.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import subprocess

NAMES = ('M4_SYSCMD_SHELL', 'CONFIGURE_ARGS', 'DEPENDS', 'PKG_FAIL_REASON',
         'PKGREVISION', 'CONFIG_SHELL', 'USE_CROSS_COMPILE',
         'PERL_BUILD_SHELL', 'PERL_RUNTIME_SHELL', 'CONFIGURE_ENV',
         'TOOLS_CAT', 'TOOLS_PATH.cat', 'TOOLS_CMD.cat', 'TOOLS_PLATFORM.cat')


def require(value, message):
    if not value:
        raise AssertionError(message)


def check(row, expected, *, dependency=False, refused=False):
    """Validate actual parser output. A printed shell is not a runtime PASS."""
    options = [word for word in shlex.split(row['CONFIGURE_ARGS'])
               if word.startswith('--with-syscmd-shell=')]
    require(bool(row['PKG_FAIL_REASON']) == refused, 'Unexpected path refusal')
    require(options == ([] if expected is None else ['--with-syscmd-shell=' + expected]),
            'M4 did not receive exactly the explicit target runtime shell')
    edges = [word for word in row['DEPENDS'].split()
             if word.endswith(':../../shells/mksh')]
    require(len(edges) == int(dependency), 'The mksh runtime edge is missing or duplicated')
    require(row['PKGREVISION'] == '1', 'The changed installed runtime needs PKGREVISION 1')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('recipe', 'profile', 'makeconf', 'shell', 'new_work'):
        parser.add_argument('--' + name.replace('_', '-'), type=Path, required=True)
    parser.add_argument('--make-arg', action='append', required=True)
    parser.add_argument('--perl-recipe', type=Path, required=True)
    parser.add_argument('--tools-darwin', type=Path, required=True)
    parser.add_argument('--tools-replace', type=Path, required=True)
    parser.add_argument('--tools-defaults', type=Path, required=True)
    parser.add_argument('--cat', type=Path, required=True)
    parser.add_argument('--only-perl', action='store_true')
    args = parser.parse_args()
    command, work = args.make_arg, args.new_work
    require(all(path.is_absolute() and path.is_file() for path in
                (args.recipe, args.profile, args.makeconf, args.shell, args.perl_recipe,
                 args.tools_darwin, args.tools_replace, args.tools_defaults, args.cat)),
            'Use explicit source files and selected host tools')
    require(work.is_absolute() and work.resolve() == work and not os.path.lexists(work),
            'Use a new absolute work directory')
    require(len(command) == 5 and command[1] == '-m' and command[3] == 'SHELL=' + str(args.shell)
            and command[4] == 'MAKECONF=' + str(args.makeconf)
            and all(os.path.isabs(path) for path in (command[0], command[2])),
            'Supply the complete accepted bmake tuple')
    require(not any(c.isspace() for c in str(args.shell)), 'The .SHELL path must be one word')
    config = args.makeconf.read_text()
    require(not any(line.startswith(('_MAKE=', 'MAKE=', 'EMBERBSD_DARWIN_METADATA='))
                    for line in config.splitlines()), 'Use a full-format or phase-neutral MAKECONF')
    lines = config.splitlines(keepends=True)
    includes = [n for n, line in enumerate(lines)
                if re.fullmatch(r'\.include\s+"[^"]*EMBERBSD-DARWIN-BOOTSTRAP-MK\.CONF"\s*\n?', line)]
    require(len(includes) == 1, 'Require the one real source profile include')
    lines[includes[0]] = '.include "' + str(args.profile) + '"\n'
    work.mkdir(mode=0o700)
    (work / 'empty-bin').mkdir()
    (work / 'devel/m4').mkdir(parents=True)
    (work / 'mk').mkdir()
    (work / 'devel/m4/Makefile').write_bytes(args.recipe.read_bytes())
    (work / 'mk/bsd.pkg.mk').write_text('# Source fixture: no package targets.\n')
    (work / 'mk/bsd.prefs.mk').write_text(
        'MACHINE_ARCH?= aarch64\nOPSYS?= Darwin\n'
        '.if ${EMBER_TEST_PROFILE:Uno} == "yes"\n'
        '.include "${MAKECONF}"\nPKGPATH= ${EMBER_TEST_RECIPE}\nBSD_PKG_MK=1\n'
        '.include "${MAKECONF}"\n.include "${MAKECONF}"\n.endif\n')
    makeconf = work / 'mk.conf'
    makeconf.write_text(''.join(lines))
    future = work / 'unbuilt-prefix'
    env = dict(PATH=str(work / 'empty-bin'), LC_ALL='C', TZ='UTC', TMPDIR=str(work))
    records = {}
    perl = args.perl_recipe.read_text()
    revision = next(line for line in perl.splitlines(True) if line.startswith('PKGREVISION='))
    begin, end = '# BEGIN explicit native runtime shells\n', '# END explicit native runtime shells\n'
    if begin in perl:
        require(perl.count(begin) == perl.count(end) == 1 and
                perl.index('.include "../../mk/bsd.prefs.mk"') < perl.index(begin),
                'The real Perl selector must follow bsd.prefs.mk')
        perl = perl.split(begin, 1)[1].split(end, 1)[0]
    else:
        perl = '# Unchanged old recipe has no explicit pair contract.\n'
    defaults = args.tools_defaults.read_text()
    replace = args.tools_replace.read_text()
    # Use both real generic platform/path mapping loops. Do not simulate a
    # wrapper or force the internal pkgsrc provider choice.
    cat_line = next(line for line in defaults.splitlines(True) if line.startswith('_TOOLS_VARNAME.cat='))
    start = replace.index('.for _t_ in ${_USE_TOOLS}\n', replace.index('# _TOOLS_USE_PKGSRC.<tool>'))
    end_at = replace.index('.endfor\n', start) + len('.endfor\n')
    provider_loop = replace[start:end_at]
    start = replace.index('.for _t_ in ${_USE_TOOLS}\n', replace.index('# For each of the blocks below'))
    end_at = replace.index('\n# The builtin maps', start)
    path_loop = replace[start:end_at]
    (work / 'perl-selected.mk').write_text(
        '.include "' + str(work / 'mk/bsd.prefs.mk') + '"\n' + revision + perl + '\n' +
        'TOOLS_PLATFORM.cat?= ' + str(args.cat) + '\n' +
        '.if ${EMBER_TEST_PROFILE:Uno} == "yes"\n.include "' + str(args.tools_darwin) + '"\n.endif\n' +
        'X11_TYPE=modular\n_USE_TOOLS=cat\nTOOLS_CMD.cat=' + str(work / '.tools/bin/cat') + '\n' + cat_line +
        provider_loop + path_loop)

    def query(name, values, kind='devel/m4'):
        path = work / (name + '.mk')
        path.write_text('.SHELL: name=sh path=' + str(args.shell) +
            ' hasErrCtl=no check="set -e" ignore="set +e" echoFlag=v errFlag=e\n' +
            '.include "' + str(work / ('perl-selected.mk' if kind == 'lang/perl5' else 'devel/m4/Makefile')) + '"\n')
        argv = [*command[:3], 'MAKECONF=' + str(makeconf), '-r', '-f', str(path),
                'LOCALBASE=' + str(future), 'EMBER_TEST_RECIPE=' + kind, *values,
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

    for mode in (() if args.only_perl else ('yes', 'no', 'default')):
        values = ['EMBER_TEST_PROFILE=yes', 'EMBERBSD_DARWIN_BOOTSTRAP=yes']
        if mode != 'default':
            values += ['EMBERBSD_DARWIN_METADATA=' + mode]
        check(query('profile-' + mode, values), str(future / 'bin/mksh'), dependency=True)
    for cross in (() if args.only_perl else ('no', 'yes')):
        check(query('default-cross-' + cross, ['USE_CROSS_COMPILE=' + cross, 'OPSYS=NetBSD']), None)
    for name, shell in ([] if args.only_perl else [('explicit-cross', '/target/pkg/bin/mksh'),
                        ('space-cross', '/target sdk/pkg/bin/mksh')]):
        check(query(name, ['USE_CROSS_COMPILE=yes', 'OPSYS=NetBSD', 'M4_SYSCMD_SHELL=' + shell]), shell)
    for name, value in ([] if args.only_perl else [('empty', ''), ('relative', 'bin/mksh'), ('relative-space', 'bin /target/mksh')]):
        check(query(name, ['M4_SYSCMD_SHELL=' + value]), None, refused=True)
    def perl_check(row, build=None, runtime=None, *, dependency=False, refused=False):
        require(bool(row['PKG_FAIL_REASON']) == refused, 'Unexpected Perl pair refusal')
        options = [word for word in shlex.split(row['CONFIGURE_ARGS'])
                   if word.startswith(('-Dsh=', '-Dtargetsh='))]
        expected = [] if build is None else ['-Dsh=' + build, '-Dtargetsh=' + runtime]
        require(options == expected, 'Perl build/runtime shell selection differs')
        bindings = dict(word.split('=', 1) for word in shlex.split(row['CONFIGURE_ENV']) if '=' in word)
        if build is not None:
            require(row['CONFIG_SHELL'] == build and bindings.get('PERL_BUILD_SHELL') == build,
                    'The early build shell does not match CONFIG_SHELL')
            require(bindings.get('PERL_BUILD_CAT') == row['TOOLS_CAT'] == row['TOOLS_PATH.cat'] ==
                    row['TOOLS_PLATFORM.cat'] == str(args.cat) and row['TOOLS_CAT'] != row['TOOLS_CMD.cat'],
                    'The sharp shebang must select the real accepted cat binary')
        else:
            require(not {'PERL_BUILD_SHELL', 'PERL_BUILD_CAT'} & set(bindings), 'Unset/refused Perl pair leaked a selector')
        require(row['PKGREVISION'] == '8', 'The selected Perl feature contract needs PKGREVISION 8')
        edges = [word for word in row['DEPENDS'].split() if word.endswith(':../../shells/mksh')]
        require(len(edges) == int(dependency), 'Perl mksh runtime edge is missing or duplicated')
    for mode in ('yes', 'no', 'default'):
        values = ['EMBER_TEST_PROFILE=yes', 'EMBERBSD_DARWIN_BOOTSTRAP=yes']
        if mode != 'default': values += ['EMBERBSD_DARWIN_METADATA=' + mode]
        perl_check(query('perl-profile-' + mode, values, 'lang/perl5'),
                   str(args.shell) if mode == 'yes' else str(future / 'bin/mksh'),
                   str(future / 'bin/mksh'), dependency=True)
    for cross in ('no', 'yes'):
        perl_check(query('perl-default-' + cross, ['USE_CROSS_COMPILE=' + cross], 'lang/perl5'))
    perl_check(query('perl-explicit-cross', ['USE_CROSS_COMPILE=yes',
        'PERL_BUILD_SHELL=' + str(args.shell), 'PERL_RUNTIME_SHELL=/bin/sh'], 'lang/perl5'), str(args.shell), '/bin/sh')
    perl_check(query('perl-space-runtime', ['USE_CROSS_COMPILE=yes',
        'PERL_BUILD_SHELL=' + str(args.shell), 'PERL_RUNTIME_SHELL=/target sdk/bin/sh'],
        'lang/perl5'), str(args.shell), '/target sdk/bin/sh')
    for name, values in [('missing-runtime', ['PERL_BUILD_SHELL=' + str(args.shell)]),
                         ('missing-build', ['PERL_RUNTIME_SHELL=/bin/sh']),
                         ('empty-build', ['PERL_BUILD_SHELL=', 'PERL_RUNTIME_SHELL=/bin/sh']),
                         ('relative-runtime', ['PERL_BUILD_SHELL=' + str(args.shell), 'PERL_RUNTIME_SHELL=bin/sh']),
                         ('space-build', ['PERL_BUILD_SHELL=/build sdk/bin/mksh', 'PERL_RUNTIME_SHELL=/bin/sh'])]:
        perl_check(query('perl-' + name, values, 'lang/perl5'), refused=True)
    require(not os.path.lexists(future), 'A future runtime provider was created')
    (work / 'observations.json').write_text(json.dumps(records, indent=2) + '\n')
    print(json.dumps(dict(status='PASS', scope='Source parser cases only; runtime not executed',
                          queries=len(records), observations=str(work / 'observations.json'))))


if __name__ == '__main__':
    main()
