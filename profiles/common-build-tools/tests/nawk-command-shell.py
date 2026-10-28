#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Source-only shell selector and argv checks.
"""Check the real recipe flag transport without compiling or running nawk."""
import argparse
import os
from pathlib import Path
import shlex
import subprocess


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--recipe', required=True, type=Path)
    cli.add_argument('--bmake', required=True, type=Path)
    cli.add_argument('--work', required=True, type=Path)
    cli.add_argument('--netbsd-profile', type=Path)
    cli.add_argument('--darwin-profile', type=Path)
    args = cli.parse_args()
    if not all(path.is_absolute() for path in (args.recipe, args.bmake, args.work)):
        cli.error('Select absolute paths')
    args.work.mkdir()
    recipe_dir = args.work / 'pkgsrc/lang/nawk'
    recipe_dir.mkdir(parents=True)
    prefs = args.work / 'pkgsrc/mk/bsd.prefs.mk'
    prefs.parent.mkdir()
    prefs.write_text('.if ${MAKECONF:U/dev/null} != "/dev/null"\n'
                     '.include "${MAKECONF}"\n.endif\n')
    makefile = recipe_dir / 'Makefile'
    # Evaluate the production selector and flags. Full pkgsrc includes remain
    # a separate package check; no replacement selector is used here.
    production = (args.recipe / 'Makefile').read_text().split('BUILD_TARGET=', 1)[0]
    makefile.write_text('CFLAGS= -O2\n' + production)
    env = dict(os.environ, MAKEFLAGS='', MAKECONF='/dev/null')
    command = [str(args.bmake), '-r', '-m', '/', '-f', str(makefile), 'CC=/selected/gcc16']

    def query(expression, shell=None, *, extra=()):
        variables = [] if shell is None else ['NAWK_COMMAND_SHELL=' + shell]
        return subprocess.run(command + variables + list(extra) + ['-V', expression], env=env,
                              check=True, capture_output=True, text=True).stdout.strip()

    for shell in (None, '/selected/sdk/bin/sh', '/selected/sdk+1/bin/mksh'):
        assert not query('${PKG_FAIL_REASON}', shell)
        assignments = shlex.split(query('${MAKE_FLAGS}', shell))
        plan = subprocess.run([str(args.bmake), '-r', '-n', *assignments, 'a.out'],
                              cwd=args.recipe / 'files', env=env, check=True,
                              capture_output=True, text=True).stdout
        lines = [shlex.split(line) for line in plan.splitlines()]
        assert lines and all(line[0] == '/selected/gcc16' for line in lines)
        for argv in lines:
            selected = [word for word in argv if word.startswith('-DNAWK_COMMAND_SHELL=')]
            assert selected == ([] if shell is None else ['-DNAWK_COMMAND_SHELL="' + shell + '"'])
    for shell in ('', 'relative/sh', '/selected/bad shell', '/selected/sh;false', '/selected/"sh',
                  '/selected/sh ', '/selected/\tsh'):
        assert 'NAWK_COMMAND_SHELL must be an absolute shell path' in query('${PKG_FAIL_REASON}', shell)
    if args.netbsd_profile is not None:
        if not args.netbsd_profile.is_absolute():
            cli.error('Select an absolute NetBSD profile path')
        profile_dir = args.work / 'profile'
        profile_dir.mkdir()
        profile = profile_dir / 'EMBERBSD-NETBSD-BOOTSTRAP-MK.CONF'
        original_profile = args.netbsd_profile.read_text()
        profile.write_text(original_profile)
        # This isolates the production profile and recipe selector. The real
        # pkgsrc dependency graph remains covered by netbsd-bootstrap-profile.py.
        (profile_dir / 'EMBERBSD-DEVELOPMENT-MK.CONF').write_text('# fixture: no common policy\n')
        makeconf = args.work / 'netbsd.mk.conf'
        fields = dict(EMBERBSD_NETBSD_BOOTSTRAP='yes', EMBERBSD_NETBSD_HOST_OS='NetBSD',
            EMBERBSD_NETBSD_HOST_CPU='x86_64', EMBERBSD_NETBSD_KERNEL_VERSION='11.0',
            EMBERBSD_NETBSD_PKGSRC_OPSYS_VERSION='110000',
            EMBERBSD_NETBSD_SH='/accepted/initial/bin/mksh',
            EMBERBSD_NETBSD_MAKE='/accepted/initial/bin/bmake',
            EMBERBSD_NETBSD_GMAKE='/accepted/initial/bin/gmake',
            EMBERBSD_NETBSD_UTILITY_BIN='/accepted/utilities',
            GCCBASE='/accepted/gcc16', LOCALBASE='/output', PREFIX='/output',
            WRKOBJDIR='/work', DISTDIR='/distfiles', PKG_DBDIR='/pkgdb', PACKAGES='/packages',
            EMBERBSD_NETBSD_NATIVE_TOOLS='awk grep sed uname', EMBERBSD_NETBSD_JOBS='1',
            BSD_PKG_MK='yes', PKGPATH='lang/nawk')
        for name in ('CC', 'CXX', 'CPP'):
            fields['EMBERBSD_GCC16_SEED_' + name] = '/accepted/gcc16/bin/' + name.lower()
        for name in ('AS', 'LD', 'AR', 'RANLIB', 'NM', 'STRIP'):
            fields['EMBERBSD_GCC16_' + name] = '/accepted/gcc16/bin/' + name.lower()
        for role in ('awk', 'grep', 'sed', 'uname'):
            fields['EMBERBSD_NETBSD_TOOL.' + role] = '/accepted/utilities/' + role
        makeconf.write_text(''.join(name + '= ' + value + '\n' for name, value in fields.items())
                           + '.include "' + str(profile) + '"\n')
        extra = ('MAKECONF=' + str(makeconf),)

        def selected_flag():
            assignments = shlex.split(query('${MAKE_FLAGS}', extra=extra))
            flags = next(field.split('=', 1)[1] for field in assignments if field.startswith('CFLAGS='))
            return [word for word in shlex.split(flags) if word.startswith('-DNAWK_COMMAND_SHELL=')]

        expected = ['-DNAWK_COMMAND_SHELL="/output/bin/mksh"']
        assert selected_flag() == expected
        assert query('${EMBERBSD_NETBSD_SH}', extra=extra) == '/output/bin/mksh'
        for kind in ('DEPENDS', 'BOOTSTRAP_DEPENDS'):
            assert 'mksh>=59b:../../shells/mksh' in shlex.split(query('${' + kind + '}', extra=extra))
        makefile.write_text('CFLAGS= -O2\n' + production +
            'NAWK_COMMAND_SHELL= /outer/config/sh\n.include "${MAKECONF}"\n')
        assert selected_flag() == expected
        makefile.write_text('CFLAGS= -O2\n' + production)
        profile.write_text('\n'.join(line for line in original_profile.splitlines()
                                    if not line.startswith('NAWK_COMMAND_SHELL:=')) + '\n')
        assert selected_flag() != expected, 'missing profile binding escaped the control'
        profile.write_text(original_profile)
        makefile.write_text('CFLAGS= -O2\n' + production.replace('.include "../../mk/bsd.prefs.mk"\n', ''))
        assert selected_flag() != expected, 'late preference loading escaped the control'
        makefile.write_text('CFLAGS= -O2\n' + production)
        assert selected_flag() == expected
        print('PASS: production NetBSD profile, runtime shell edges, early preferences, repeated selection, two mutations')
    if args.darwin_profile is not None:
        if not args.darwin_profile.is_absolute():
            cli.error('Select an absolute Darwin profile path')
        profile_dir = args.work / 'darwin-profile'
        profile_dir.mkdir()
        profile = profile_dir / 'EMBERBSD-DARWIN-BOOTSTRAP-MK.CONF'
        original_profile = args.darwin_profile.read_text()
        profile.write_text(original_profile)
        (profile_dir / 'EMBERBSD-DEVELOPMENT-MK.CONF').write_text('# no common fixture policy\n')
        (profile_dir / 'EMBERBSD-DEFAULTS-MK.CONF').write_text('# no common fixture defaults\n')
        abi = args.work / 'abi'
        (abi / 'usr/lib').mkdir(parents=True)
        (abi / 'usr/lib/libiconv.tbd').write_text('source fixture only\n')
        early = 'awk basename cat cut date dirname env expr grep head id pwd sed sort tail tr uname uniq wc'
        # The fixture supplies the explicit GCC route inputs (EMBERBSD_GCC16_*).
        fields = dict(EMBERBSD_DARWIN_BOOTSTRAP='yes', EMBERBSD_COMPILER_FAMILY='gcc',
            EMBERBSD_DARWIN_HOST_OS='Darwin',
            EMBERBSD_DARWIN_HOST_CPU='aarch64', EMBERBSD_DARWIN_HOST_KERNEL_VERSION='25.0',
            EMBERBSD_DARWIN_HOST_PRODUCT_VERSION='26.0', EMBERBSD_DARWIN_HOST_PKGSRC_OPSYS_VERSION='260000',
            EMBERBSD_DARWIN_SH='/selected/initial/mksh', EMBERBSD_DARWIN_MAKE='/selected/initial/bmake',
            EMBERBSD_DARWIN_GMAKE='/selected/initial/gmake', EMBERBSD_DARWIN_UTILITY_BIN='/selected/utilities',
            LOCALBASE='/output', WRKOBJDIR='/work', DISTDIR='/distfiles', PKG_DBDIR='/pkgdb', PACKAGES='/packages',
            OSX_SDK_PATH=str(abi), EMBERBSD_GCC16_DARWIN_SDK_VERSION='27.0', MACOSX_DEPLOYMENT_TARGET='26.0',
            EMBERBSD_DARWIN_JOBS='1', EMBERBSD_DARWIN_CPU_BUDGET='1', EMBERBSD_DARWIN_NATIVE_TOOLS=early,
            EMBERBSD_DARWIN_SOURCE_TOOLS='gzip gunzip gzcat',
            NATIVE_PKG_ADMIN_CMD='/selected/pkg_admin', NATIVE_PKG_INFO_CMD='/selected/pkg_info',
            BSD_PKG_MK='yes', PKGPATH='lang/nawk')
        for name in ('CC', 'CXX', 'CPP', 'LLVM_MC', 'LD64_LLD', 'DSYMUTIL', 'AR', 'RANLIB', 'NM', 'STRIP'):
            fields['EMBERBSD_GCC16_' + ('SEED_' if name in ('CC', 'CXX', 'CPP') else '') + name] = '/selected/' + name.lower()
        for role in early.split():
            fields['EMBERBSD_DARWIN_TOOL.' + role] = '/selected/utilities/' + role
        makeconf = args.work / 'darwin.mk.conf'
        makeconf.write_text(''.join(name + '= ' + value + '\n' for name, value in fields.items())
                           + ('.include "' + str(profile) + '"\n') * 2)
        for mode in ('yes', 'no'):
            extra = ('MAKECONF=' + str(makeconf), 'EMBERBSD_DARWIN_METADATA=' + mode)
            assert query('${NAWK_COMMAND_SHELL}', extra=extra) == '/output/bin/mksh'
            assignments = shlex.split(query('${MAKE_FLAGS}', extra=extra))
            flags = next(value.split('=', 1)[1] for value in assignments if value.startswith('CFLAGS='))
            assert shlex.split(flags).count('-DNAWK_COMMAND_SHELL="/output/bin/mksh"') == 1
            assert shlex.split(query('${DEPENDS}', extra=extra)).count('mksh>=59b:../../shells/mksh') == 1
        profile.write_text('\n'.join(line for line in original_profile.splitlines()
                                    if not line.startswith('NAWK_COMMAND_SHELL=')) + '\n')
        assert query('${NAWK_COMMAND_SHELL}', extra=extra) != '/output/bin/mksh'
        profile.write_text(original_profile)
        print('PASS: Darwin runtime shell, recipe compiler flag, one dependency, repeated includes, causal mutation')
    print('PASS: default and selected shell compiler argv; seven invalid paths rejected')
    print('SOURCE ONLY: no compiler, shell adapter or package execution')


if __name__ == '__main__':
    main()
