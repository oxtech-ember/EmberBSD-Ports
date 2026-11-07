#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted). Evaluates the Darwin bootstrap tool profile.
"""Publish install_name_tool in the package tools directory.

usage: darwin-bootstrap-install-name-tool.py BMAKE NEW_WORK

GNU libtool-reloc runs bare install_name_tool. The Darwin bootstrap PATH
contains the utility directory and the tools directory, not /usr/bin.
The profile must create that name and point it at the selected command,
defaulting to /usr/bin/install_name_tool. gettext-tools stays
gettext-tools-1.0nb9 and keeps --enable-relocatable.
"""
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CONF = ROOT / 'profiles/development-toolchain/darwin-bootstrap.mk.conf'
EARLY = ('awk basename cat cut date dirname env expr grep head id pwd '
         'sed sort tail tr uname uniq wc').split()


def require(value, message):
    if not value:
        raise AssertionError(message)


def evaluate(bmake, work, install_name_tool):
    sdk = work / 'sdk'
    (sdk / 'usr/lib').mkdir(parents=True)
    (sdk / 'usr/lib/libiconv.tbd').write_text('tbd\n')
    profile = work / 'profile'
    profile.mkdir()
    shutil.copy(CONF, profile / 'darwin-bootstrap.mk.conf')
    (profile / 'EMBERBSD-DEVELOPMENT-MK.CONF').write_text('# test stub\n')
    lines = [
        'EMBERBSD_DARWIN_BOOTSTRAP= yes',
        'EMBERBSD_COMPILER_FAMILY= clang',
        'EMBERBSD_DARWIN_TOOL_PHASE= initial',
        'USE_CROSS_COMPILE= no',
        'EMBERBSD_DARWIN_HOST_OS= Darwin',
        'EMBERBSD_DARWIN_HOST_CPU= aarch64',
        'EMBERBSD_DARWIN_HOST_KERNEL_VERSION= 25.0.0',
        'EMBERBSD_DARWIN_HOST_PRODUCT_VERSION= 26.0',
        'EMBERBSD_DARWIN_HOST_PKGSRC_OPSYS_VERSION= 260000',
        'EMBERBSD_DARWIN_SDK_VERSION= 26.0',
        'MACOSX_DEPLOYMENT_TARGET= 26.0',
        'EMBERBSD_DARWIN_JOBS= 1',
        'EMBERBSD_DARWIN_CPU_BUDGET= 1',
        f'EMBERBSD_DARWIN_SH= {work}/bin/mksh',
        f'EMBERBSD_DARWIN_UTILITY_BIN= {work}/utility',
        f'WRKOBJDIR= {work}/obj',
        f'DISTDIR= {work}/dist',
        f'PACKAGES= {work}/packages',
        f'LOCALBASE= {work}/prefix',
        f'PKG_DBDIR= {work}/prefix/pkgdb',
        f'OSX_SDK_PATH= {sdk}',
        f'EMBERBSD_DARWIN_MAKE= {bmake}',
        f'EMBERBSD_DARWIN_GMAKE= {work}/bin/gmake',
        f'EMBERBSD_DARWIN_SEED_CC= {work}/bin/clang',
        f'EMBERBSD_DARWIN_SEED_CXX= {work}/bin/clang++',
        f'EMBERBSD_DARWIN_SEED_CPP= {work}/bin/clang -E',
        f'EMBERBSD_DARWIN_SEED_AS= {work}/bin/clang',
        f'EMBERBSD_DARWIN_LLVM_MC= {work}/bin/llvm-mc',
        f'EMBERBSD_DARWIN_LD64_LLD= {work}/bin/ld64.lld',
        f'EMBERBSD_DARWIN_DSYMUTIL= {work}/bin/dsymutil',
        f'EMBERBSD_DARWIN_AR= {work}/bin/llvm-ar',
        f'EMBERBSD_DARWIN_RANLIB= {work}/bin/llvm-ranlib',
        f'EMBERBSD_DARWIN_NM= {work}/bin/llvm-nm',
        f'EMBERBSD_DARWIN_STRIP= {work}/bin/llvm-strip',
        'EMBERBSD_DARWIN_NATIVE_TOOLS= ' + ' '.join(EARLY),
        'EMBERBSD_DARWIN_SOURCE_TOOLS= gzip gunzip gzcat',
        'NATIVE_PKG_ADMIN_CMD= ' + f'{work}/bin/pkg_admin',
        'NATIVE_PKG_INFO_CMD= ' + f'{work}/bin/pkg_info',
    ]
    lines += [f'EMBERBSD_DARWIN_TOOL.{name}= {work}/bin/{name}' for name in EARLY]
    if install_name_tool is not None:
        lines.append(f'EMBERBSD_DARWIN_INSTALL_NAME_TOOL= {install_name_tool}')
    lines += [
        f'.include "{profile}/darwin-bootstrap.mk.conf"',
        'all:',
        '\t@printf \'%s\\n\' ${TOOLS_CREATE:Q}',
        '\t@printf \'%s\\n\' ${TOOLS_PATH.install_name_tool:Q}',
    ]
    (work / 'Makefile').write_text('\n'.join(lines) + '\n')
    result = subprocess.run([bmake, '-C', str(work), '-f', 'Makefile', 'all'],
                            capture_output=True, text=True, env={'PATH': '/usr/bin:/bin'})
    require(result.returncode == 0, result.stderr.strip() or result.stdout)
    created, path = result.stdout.splitlines()
    return created.split(), path


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    bmake, work = sys.argv[1], Path(sys.argv[2])
    require(Path(bmake).is_absolute() and work.is_absolute(), 'paths must be absolute')
    require(not work.exists(), 'NEW_WORK must not exist')
    work.mkdir()
    created, path = evaluate(bmake, work / 'default', None)
    require(created.count('install_name_tool') == 1, f'install_name_tool create count: {created}')
    for tool in ('ar', 'nm', 'ranlib'):
        require(created.count(tool) == 1, f'{tool} is no longer created once: {created}')
    require(path == '/usr/bin/install_name_tool', f'default tool is {path!r}')
    selected = work / 'selected/install_name_tool'
    selected.parent.mkdir()
    selected.write_text('#!/bin/sh\nprintf \'%s\\n\' "$@"\n')
    selected.chmod(selected.stat().st_mode | stat.S_IEXEC)
    created, path = evaluate(bmake, work / 'selected', selected)
    require(created.count('install_name_tool') == 1 and path == str(selected),
            f'selected tool was not kept: {created} {path}')
    tools = work / 'tools'
    tools.mkdir()
    os.symlink(selected, tools / 'install_name_tool')
    decoy = work / 'decoy'
    decoy.mkdir()
    missing = decoy / 'install_name_tool'
    missing.write_text('#!/bin/sh\necho decoy >&2\nexit 97\n')
    missing.chmod(0o755)
    command = 'install_name_tool -id @rpath/libgettextlib-1.0.dylib ./.libs/libgettextlib-1.0.dylib'
    found = subprocess.run(['/bin/sh', '-c', command], cwd=work, capture_output=True, text=True,
                           env={'PATH': str(tools)})
    require(found.returncode == 0, found.stderr)
    require(found.stdout.splitlines() ==
            ['-id', '@rpath/libgettextlib-1.0.dylib', './.libs/libgettextlib-1.0.dylib'],
            f'wrapper arguments were {found.stdout!r}')
    (work / 'empty').mkdir()
    hidden = subprocess.run(['/bin/sh', '-c', command], cwd=work, capture_output=True, text=True,
                            env={'PATH': str(work / 'empty')})
    require(hidden.returncode == 127, f'bare command without the tools directory exited {hidden.returncode}')
    relative = work / 'relative'
    shutil.copytree(work / 'selected', relative)
    makefile = (relative / 'Makefile').read_text().replace(
        f'EMBERBSD_DARWIN_INSTALL_NAME_TOOL= {selected}',
        'EMBERBSD_DARWIN_INSTALL_NAME_TOOL= install_name_tool')
    (relative / 'Makefile').write_text(makefile)
    rejected = subprocess.run([bmake, '-C', str(relative), '-f', 'Makefile', 'all'],
                              capture_output=True, text=True, env={'PATH': '/usr/bin:/bin'})
    require(rejected.returncode != 0 and 'one absolute install_name_tool' in rejected.stderr,
            f'relative install_name_tool was accepted: {rejected.returncode} {rejected.stderr}')
    recipe = (ROOT / 'profiles/common-build-tools/patches/gettext-external-recipe.patch').read_text()
    require('--enable-relocatable' in recipe, 'relocatable gettext-tools publisher was removed')
    identity = 'gettext-tools-1.0nb9'
    for relative in ('profiles/common-build-tools/tests/gettext-bootstrap-options.py',
                     'profiles/common-build-tools/tests/gettext-native-lifecycle.py',
                     'profiles/development-toolchain/darwin-bootstrap.md'):
        text = (ROOT / relative).read_text()
        require(identity in text and 'gettext-tools-1.0nb7' not in text,
                f'{relative} does not keep {identity}')
    print('PASS: Darwin bootstrap publishes install_name_tool and keeps gettext-tools nb9')


if __name__ == '__main__':
    main()
