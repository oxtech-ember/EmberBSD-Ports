#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Evaluate compiler families, wrapper arguments and shared defaults with real bmake."""
import argparse
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--bmake', type=Path, required=True)
parser.add_argument('--shell', type=Path, required=True)
parser.add_argument('--clang-module', type=Path, required=True,
                    help='mk/compiler/clang.mk from the current Ports export')
parser.add_argument('--policy', type=Path, help='Optional original policy for a causal failure check')
args = parser.parse_args()
for tool in (args.bmake, args.shell):
    if not tool.is_absolute() or not os.access(tool, os.X_OK):
        parser.error('Use absolute executable bmake and shell paths')
root = Path(__file__).resolve().parents[3]
with tempfile.TemporaryDirectory(prefix='darwin-family-') as temporary:
    work = Path(temporary)
    prefix = work / 'prefix'
    (prefix / 'bin').mkdir(parents=True)
    sdk = work / 'MacOSX.sdk'
    (sdk / 'usr/lib').mkdir(parents=True)
    (sdk / 'usr/lib/libiconv.tbd').touch()
    for name in ('clang', 'clang++', 'clang-cpp', 'gcc', 'g++', 'cpp'):
        path = prefix / 'bin' / name
        path.write_text('#!' + str(args.shell) + '\nprintf "23.1.4\\n"\n')
        path.chmod(0o755)
    policy = work / 'darwin.mk'
    shutil.copyfile(args.policy or root / 'profiles/development-toolchain/darwin-bootstrap.mk.conf', policy)
    shutil.copyfile(root / 'profiles/development-toolchain/mk.conf',
                    work / 'EMBERBSD-DEVELOPMENT-MK.CONF')
    shutil.copyfile(root / 'pkgsrc/defaults.mk.conf', work / 'EMBERBSD-DEFAULTS-MK.CONF')
    shutil.copyfile(root / 'pkgsrc/versions.mk', work / 'EMBERBSD-VERSIONS.MK')
    (work / 'mk/compiler').mkdir(parents=True)
    (work / 'lang/fixture').mkdir(parents=True)
    (work / 'mk/bsd.prefs.mk').touch()
    (work / 'mk/compiler/gcc-style-args.mk').touch()
    shutil.copyfile(args.clang_module, work / 'mk/compiler/clang.mk')
    common = {
        'EMBERBSD_DARWIN_BOOTSTRAP': 'yes', 'EMBERBSD_DARWIN_METADATA': 'yes',
        'EMBERBSD_DARWIN_HOST_OS': 'Darwin', 'EMBERBSD_DARWIN_HOST_CPU': 'aarch64',
        'EMBERBSD_DARWIN_HOST_KERNEL_VERSION': '26.0.0',
        'EMBERBSD_DARWIN_HOST_PRODUCT_VERSION': '27.0.1',
        'EMBERBSD_DARWIN_HOST_PKGSRC_OPSYS_VERSION': '270001',
        'MACOSX_DEPLOYMENT_TARGET': '26.0', 'EMBERBSD_DARWIN_JOBS': '1',
        'EMBERBSD_DARWIN_CPU_BUDGET': '1', 'EMBERBSD_DARWIN_SH': str(args.shell),
        'EMBERBSD_DARWIN_MAKE': str(args.bmake), 'EMBERBSD_DARWIN_GMAKE': str(args.bmake),
        'EMBERBSD_DARWIN_UTILITY_BIN': str(prefix / 'bin'),
        'WRKOBJDIR': str(work / 'obj'), 'DISTDIR': str(work / 'distfiles'),
        'PACKAGES': str(work / 'packages'), 'LOCALBASE': str(prefix),
        'PKG_DBDIR': str(prefix / 'pkgdb'), 'OSX_SDK_PATH': str(sdk),
        'NATIVE_PKG_ADMIN_CMD': str(prefix / 'bin/pkg_admin'),
        'NATIVE_PKG_INFO_CMD': str(prefix / 'bin/pkg_info'),
        'BSD_PKG_MK': '1', 'PKGPATH': 'lang/clang',
        'EMBERBSD_DARWIN_SOURCE_TOOLS': 'gzip gunzip gzcat',
        'EMBERBSD_DARWIN_NATIVE_TOOLS': 'awk basename cat cut date dirname env expr grep head id pwd sed sort tail tr uname uniq wc',
        'USE_LANGUAGES': 'c c++', '_PKGSRC_BARRIER': '1',
    }
    for role in common['EMBERBSD_DARWIN_NATIVE_TOOLS'].split():
        common['EMBERBSD_DARWIN_TOOL.' + role] = str(prefix / 'bin' / role)
    generic = {'EMBERBSD_DARWIN_SDK_VERSION': '27.0'}
    for role in ('LLVM_MC', 'LD64_LLD', 'DSYMUTIL', 'AR', 'RANLIB', 'NM', 'STRIP'):
        generic['EMBERBSD_DARWIN_' + role] = str(prefix / 'bin' / role.lower())
    flags = ['-isysroot', str(sdk), '-mmacosx-version-min=26.0']
    for role, name in (('CC', 'clang'), ('CXX', 'clang++'), ('CPP', 'clang')):
        generic['EMBERBSD_DARWIN_SEED_' + role] = shlex.join([str(prefix / 'bin' / name), *flags])
    generic['EMBERBSD_DARWIN_SEED_CPP'] += ' -E'
    generic['EMBERBSD_DARWIN_SEED_AS'] = generic['EMBERBSD_DARWIN_SEED_CC'] + ' -c -x assembler'
    query_names = ('PKGSRC_COMPILER', 'CC', 'CXX', 'CPP', 'AS', 'LDFLAGS',
                   'CWRAPPERS_PREPEND.cc', '_WRAP_EXTRA_ARGS.CC',
                   'PKG_CC', 'PKG_AS', 'PKG_CPP', 'CWRAPPERS_PREPEND.as',
                   '_WRAP_EXTRA_ARGS.AS', 'CWRAPPERS_PREPEND.cpp',
                   '_WRAP_EXTRA_ARGS.CPP', 'BOOTSTRAP_DEPENDS')

    def evaluate(values, wrapper=False, names=query_names):
        makefile = work / 'lang/fixture/Makefile'
        makefile.write_text(''.join(name + '= ' + value + '\n' for name, value in values.items())
                            + '.include "' + str(policy) + '"\n'
                            + ('.include "../../mk/compiler/clang.mk"\n' if wrapper else ''))
        command = [str(args.bmake), '-r', '-f', str(makefile), 'SHELL=' + str(args.shell)]
        for name in names:
            command += ['-V', '${' + name + '}']
        result = subprocess.run(command, cwd=makefile.parent,
                                env={'PATH': str(prefix / 'bin'), 'LC_ALL': 'C',
                                     'MAKECONF': str(work / 'unused.mk')}, capture_output=True)
        return result, dict(zip(names, result.stdout.decode().splitlines()))

    result, values = evaluate(dict(common, **generic), wrapper=True)
    assert result.returncode == 0, result.stderr
    assert values['PKGSRC_COMPILER'] == 'clang'
    assert values['CC'] == values['PKG_CC'] == str(prefix / 'bin/clang')
    assert values['AS'] == 'as' and values['CPP'] == 'cpp'
    assert values['PKG_AS'] == values['PKG_CPP'] == str(prefix / 'bin/clang')
    for suffix, expected in (('AS', [*flags, '-c', '-x', 'assembler']), ('CPP', [*flags, '-E'])):
        assert shlex.split(values['CWRAPPERS_PREPEND.' + suffix.lower()]) == expected
        assert shlex.split(values['_WRAP_EXTRA_ARGS.' + suffix]) == expected
    assert shlex.split(values['CWRAPPERS_PREPEND.cc']) == flags
    assert shlex.split(values['_WRAP_EXTRA_ARGS.CC']) == flags
    assert values['LDFLAGS'] == ''
    assert 'gcc16' not in values['BOOTSTRAP_DEPENDS']
    assert 'bsdinstall' in values['BOOTSTRAP_DEPENDS']
    no_tail = dict(common, **generic)
    for role in ('AS', 'CC', 'CPP', 'CXX'):
        key = 'EMBERBSD_DARWIN_SEED_' + role
        no_tail[key] = shlex.split(no_tail[key])[0]
    result, values = evaluate(no_tail, wrapper=True)
    assert result.returncode == 0, result.stderr
    for key in ('CWRAPPERS_PREPEND.cc', '_WRAP_EXTRA_ARGS.CC',
                'CWRAPPERS_PREPEND.as', '_WRAP_EXTRA_ARGS.AS',
                'CWRAPPERS_PREPEND.cpp', '_WRAP_EXTRA_ARGS.CPP'):
        assert values[key] == '', (key, values[key])
    for bad_family in ('auto', 'gcc clang', ''):
        result, _ = evaluate(dict(common, **generic, EMBERBSD_COMPILER_FAMILY=bad_family))
        assert result.returncode != 0 and b'compiler_family' not in result.stdout
    for missing in ('EMBERBSD_DARWIN_SEED_CXX', 'EMBERBSD_DARWIN_SEED_AS'):
        invalid = dict(common, **generic)
        del invalid[missing]
        result, _ = evaluate(invalid)
        assert result.returncode != 0, missing
    absent = dict(common, **generic)
    absent['EMBERBSD_DARWIN_SEED_CC'] = str(prefix / 'bin/absent-clang')
    result, _ = evaluate(absent, wrapper=True)
    assert result.returncode != 0 and b'selected Clang driver is missing' in result.stderr
    gcc = dict(common, EMBERBSD_COMPILER_FAMILY='gcc', PKGPATH='lang/gcc16')
    for key, value in generic.items():
        if key == 'EMBERBSD_DARWIN_SEED_AS':
            continue
        legacy = key.replace('EMBERBSD_DARWIN_', 'EMBERBSD_GCC16_')
        if key == 'EMBERBSD_DARWIN_SDK_VERSION':
            legacy = 'EMBERBSD_GCC16_DARWIN_SDK_VERSION'
        for old, new in (('clang++', 'g++'), ('clang-cpp', 'cpp'), ('clang', 'gcc')):
            value = value.replace('/bin/' + old, '/bin/' + new)
        gcc[legacy] = value
    result, values = evaluate(gcc)
    assert result.returncode == 0, result.stderr
    assert values['PKGSRC_COMPILER'] == 'gcc'
    for flag in ('-static-libstdc++', '-static-libgcc', '-nodefaultrpaths'):
        assert shlex.split(values['LDFLAGS']).count(flag) == 1
    assert shlex.split(values['CC']) == [str(prefix / 'bin/gcc'), *flags]
    # The shared defaults apply on the read with PKGPATH: licenses and one
    # version of each family. The bootstrap does not turn the Mach-O checker on.
    policy_names = ('PKG_FAIL_REASON', 'ACCEPTABLE_LICENSES', 'MACHO_USE_LOAD_COMMANDS')
    for pkgpath, rejected in (('lang/python314', True), ('lang/python315', False)):
        result, values = evaluate(dict(common, **generic, OPSYS='Darwin', PKGPATH=pkgpath),
                                  names=policy_names)
        assert result.returncode == 0, result.stderr
        reason = 'EmberBSD keeps only lang/python315 of lang/python[0-9]*'
        assert (reason in values['PKG_FAIL_REASON']) == rejected, (pkgpath, values['PKG_FAIL_REASON'])
        for license in ('esdl-license', 'gnu-agpl-v3', 'apple-public-source-license'):
            assert license in values['ACCEPTABLE_LICENSES'].split(), license
        assert values['MACHO_USE_LOAD_COMMANDS'] == '', values['MACHO_USE_LOAD_COMMANDS']

    # mk/bsd.prefs.mk reads MAKECONF twice; PKGPATH exists only on the later
    # read, after ACCEPTABLE_LICENSES?= ${DEFAULT_ACCEPTABLE_LICENSES}. A recipe
    # can turn the Mach-O checker on before bsd.prefs.mk.
    def two_reads(recipe_macho):
        first = {name: value for name, value in dict(common, **generic, OPSYS='Darwin').items()
                 if name != 'PKGPATH'}
        makefile = work / 'lang/fixture/Makefile'
        makefile.write_text(''.join(name + '= ' + value + '\n' for name, value in first.items())
                            + ('MACHO_USE_LOAD_COMMANDS= ' + recipe_macho + '\n' if recipe_macho else '')
                            + '.include "' + str(policy) + '"\n'
                            + 'ACCEPTABLE_LICENSES?= ${DEFAULT_ACCEPTABLE_LICENSES}\n'
                            + 'PKGPATH= lang/python314\n'
                            + '.include "' + str(policy) + '"\n')
        result = subprocess.run([str(args.bmake), '-r', '-f', str(makefile), 'SHELL=' + str(args.shell),
                                 '-dV', '-V', '${PKG_FAIL_REASON}', '-V', 'ACCEPTABLE_LICENSES',
                                 '-V', '${MACHO_USE_LOAD_COMMANDS}'], cwd=makefile.parent,
                                env={'PATH': str(prefix / 'bin'), 'LC_ALL': 'C',
                                     'MAKECONF': str(work / 'unused.mk')}, capture_output=True)
        assert result.returncode == 0, result.stderr
        return result.stdout.decode().splitlines()

    # 'no' differs from the defaults' value, so it shows the recipe value.
    for recipe_macho, expected in ((None, ''), ('yes', 'yes'), ('no', 'no')):
        reason, licenses, macho = two_reads(recipe_macho)
        assert 'EmberBSD keeps only lang/python315' in reason, ('two reads', reason)
        assert '${DEFAULT_ACCEPTABLE_LICENSES}' in licenses.split(), ('two reads', licenses)
        assert macho == expected, ('recipe Mach-O choice', recipe_macho, macho)
print('PASS: Clang default, exact wrapper/assembler argv, invalid/missing inputs, explicit legacy GCC route,'
      ' shared licenses and version policy on the later MAKECONF read')
