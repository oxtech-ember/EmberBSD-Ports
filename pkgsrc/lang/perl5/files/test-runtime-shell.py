#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Check Perl runtime shell dependencies through the production make rules.

Unrelated pkgsrc includes are omitted; the real cross rules and the Perl
branches of both bootstrap profiles remain active. No package is built.
"""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bmake', type=Path, required=True)
    parser.add_argument('--sed', type=Path, required=True)
    parser.add_argument('--work-parent', type=Path, required=True)
    args = parser.parse_args()
    recipe = Path(__file__).resolve().parents[1]
    ports = recipe.parents[2]
    source = (recipe / 'Makefile').read_text()
    production = '\n'.join(
        '.include "' + str(recipe / 'cross.mk') + '"' if line == '.include "cross.mk"'
        else '' if line.startswith('.include ') else line
        for line in source.splitlines())
    profiles = {}
    for name in ('darwin', 'netbsd'):
        profile = (ports / 'profiles/development-toolchain' / (name + '-bootstrap.mk.conf')).read_text()
        branch = profile.split('.    elif ${PKGPATH} == "lang/perl5"\n', 1)[1]
        profiles[name] = branch.split('.    elif ', 1)[0]
    prefix = '/selected/runtime'
    shell = prefix + '/bin/mksh'
    dependency = 'mksh>=59b:../../shells/mksh'
    env = dict(os.environ, MAKEFLAGS='', MAKECONF='/dev/null')
    with tempfile.TemporaryDirectory(prefix='perl-shell-', dir=args.work_parent) as temporary:
        fixture = Path(temporary) / 'Makefile'

        def check(name, *, cross=False, policy='', values=(), expected=True, body=production):
            fixture.write_text('''OPSYS= Darwin
MACHINE_ARCH= aarch64
MACHINE_PLATFORM= Darwin-27.0-aarch64
PKGSRC_COMPILER= clang
PKG_OPTIONS= perl-64bitauto threads
LOCALBASE= /selected/runtime
PREFIX= ${LOCALBASE}
SH= ${LOCALBASE}/bin/mksh
CONFIG_SHELL= ${SH}
TOOLS_PLATFORM.ar= ${LOCALBASE}/bin/llvm-ar
TOOLS_SH= ${SH}
PKGVERSION_NOREV= 5.44.0
DISTNAME= perl-5.44.0
EMBERBSD_DARWIN_SH= /selected/build/bin/mksh
EMBERBSD_NETBSD_SH= /selected/build/bin/mksh
''' + policy + '\n' + body)
            argv = [str(args.bmake), '-r', '-m', '/', '-f', str(fixture),
                    'FILESDIR=' + str(recipe / 'files'),
                    'SED=' + str(args.sed),
                    'USE_CROSS_COMPILE=' + ('yes' if cross else 'no'), *values,
                    '-V', '${DEPENDS}', '-V', '${PERLLINK_SH}',
                    '-V', '${PKG_FAIL_REASON}']
            if cross:
                argv += ['OPSYS=NetBSD', 'MACHINE_PLATFORM=NetBSD-11.0-aarch64']
            result = subprocess.run(argv, env=env, capture_output=True, text=True, check=True)
            dependencies, perllink, errors = result.stdout.splitlines()
            assert not errors, (name, errors)
            edges = [item for item in dependencies.split() if item.endswith(':../../shells/mksh')]
            assert edges == ([dependency] if expected else []), (name, edges)
            assert perllink == ('/bin/sh' if cross or 'PERLLINK_SH=/bin/sh' in values else
                                '/bin/sh' if 'SH=/bin/sh' in values else shell), (name, perllink)

        check('native outside bootstrap')
        for name, policy in profiles.items():
            check(name + ' bootstrap', policy=policy)
        check('native base shell', values=('SH=/bin/sh',), expected=False)
        check('cross base shell', cross=True, expected=False)
        check('cross explicit base shell', cross=True, expected=False,
              values=('PERL_BUILD_SHELL=/selected/build/bin/mksh', 'PERL_RUNTIME_SHELL=/bin/sh'))
        check('native explicit base shells', expected=False,
              values=('PERL_BUILD_SHELL=/selected/build/bin/mksh', 'PERL_RUNTIME_SHELL=/bin/sh',
                      'PERLLINK_SH=/bin/sh'))
        check('native embedded package shell', values=('PERL_BUILD_SHELL=/selected/build/bin/mksh',
              'PERL_RUNTIME_SHELL=' + shell, 'PERLLINK_SH=/bin/sh'))
        check('native perllink package shell', values=('PERL_BUILD_SHELL=/selected/build/bin/mksh',
              'PERL_RUNTIME_SHELL=/bin/sh'))
        assert production.count('DEPENDS+= mksh>=59b:../../shells/mksh') == 1
        try:
            check('deleted owner dependency', body=production.replace(
                'DEPENDS+= mksh>=59b:../../shells/mksh', ''))
        except AssertionError as error:
            assert error.args == (('deleted owner dependency', []),), error
        else:
            raise AssertionError('removing the recipe dependency escaped the regression')
    print('PASS: nine runtime-shell metadata cases and missing-dependency causal control; no build/install')


if __name__ == '__main__':
    main()
