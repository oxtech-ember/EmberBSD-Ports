#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Run the real graphics profile in pkgsrc with declared cross-input fixtures.

No compiler executes and the synthetic target inputs cannot compile code.
The common cross producer and target runtime have separate acceptance tests.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('pkgsrc', 'host-prefix', 'utility-path', 'work'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    if not args.work.is_absolute() or args.work.exists():
        parser.error('use a new absolute work directory')
    args.work.mkdir()
    owner = Path(__file__).resolve().parents[1]
    tree = args.work/'pkgsrc';tree.mkdir();(tree/'devel').mkdir()
    for entry in args.pkgsrc.iterdir():
        if entry.name not in ('devel', 'EMBERBSD-COMMON-GRAPHICS-MK.CONF'):
            (tree/entry.name).symlink_to(entry.resolve(), target_is_directory=entry.is_dir())
    for entry in (args.pkgsrc/'devel').iterdir():
        (tree/'devel'/entry.name).symlink_to(entry.resolve(), target_is_directory=entry.is_dir())
    shutil.copyfile(owner/'mk.conf', tree/'EMBERBSD-COMMON-GRAPHICS-MK.CONF')
    recipe = tree/'devel/graphics-family-fixture';recipe.mkdir()
    (recipe/'Makefile').write_text('DISTNAME=graphics-family-fixture-1.0\nCATEGORIES=devel\n'
        'MASTER_SITES=\nLICENSE=2-clause-bsd\nCOMMENT=Metadata-only profile fixture\n'
        'USE_LANGUAGES=\n.include "../../mk/bsd.pkg.mk"\n')
    (recipe/'PLIST').write_text('@comment metadata-only fixture\n')
    (recipe/'DESCR').write_text('Graphics compiler-family contract fixture.\n')
    target = args.work/'target-metadata';(target/'usr/include').mkdir(parents=True)
    (target/'usr/include/stddef.h').write_text('#error metadata fixture must not compile\n')
    tools = args.work/'target-tools';tools.mkdir()
    prefix = args.host_prefix
    config = args.work/'mk.conf'
    config.write_text('''
LOCALBASE=@PREFIX@
PYTHON_VERSION_DEFAULT=315
PKGSRC_COMPILER?=clang
PKG_TOOLS_BIN=@PREFIX@/sbin
NATIVE_PKG_TOOLS_BIN=@PREFIX@/sbin
USE_CROSS_COMPILE?=yes
.if ${USE_CROSS_COMPILE:tl} == "yes"
CROSS_OPSYS=NetBSD
CROSS_OS_VERSION=11.0
CROSS_MACHINE_ARCH?=x86_64
CROSS_OPSYS_VERSION=110000
CROSS_LOWER_OPSYS=netbsd
CROSS_LOWER_OPSYS_VERSUFFIX=
CROSS_LOWER_VARIANT_VERSION=
CROSS_LOWER_VENDOR=
CROSS_LOWER_OS_VARIANT=
CROSS_OBJECT_FMT=ELF
CROSS_LOCALBASE=/usr/pkg
CROSS_DESTDIR=@SYSROOT@
TOOLDIR=@TOOLS@
CLANGBASE=@TOOLS@
EMBERBSD_CROSS_TOOLS=@TOOLS@
EMBERBSD_CROSS_SYSROOT=@SYSROOT@
EMBERBSD_CROSS_HOST_PREFIX=@PREFIX@
.endif
EMBERBSD_COMMON_GRAPHICS_CROSS=yes
.if defined(BSD_PKG_MK)
.include "@TREE@/EMBERBSD-COMMON-GRAPHICS-MK.CONF"
.endif
'''.replace('@PREFIX@', str(prefix)).replace('@SYSROOT@', str(target)).replace('@TOOLS@', str(tools)).replace('@TREE@', str(tree)))
    env = dict(os.environ, PATH=str(args.utility_path), TMPDIR=str(args.work))
    env.pop('EMBERBSD_DARWIN_BOOTSTRAP', None)
    base = [str(prefix/'bin/bmake'), '-m', str(prefix/'share/mk'),
        'SHELL='+str(prefix/'bin/mksh'), '-C', str(recipe), 'MAKECONF='+str(config),
        'WRKOBJDIR='+str(args.work/'objects')]
    variables = ['PKG_FAIL_REASON', 'PKGSRC_COMPILER', 'OPSYS', 'MACHINE_ARCH',
                 'TOOLBASE', 'CROSS_DESTDIR', 'EMBERBSD_COMMON_GRAPHICS']
    results = {}

    def case(name, extra=(), error=None, native=False):
        command = [*base, *extra, *[item for var in variables for item in ('-V', '${'+var+'}')]]
        result = subprocess.run(command, env=env, capture_output=True, text=True)
        (args.work/(name+'.log')).write_text(result.stdout+result.stderr)
        assert not result.returncode, result.stderr
        lines = result.stdout.splitlines();assert len(lines)==len(variables), result.stdout
        values = dict(zip(variables, lines))
        if error:
            assert error in values['PKG_FAIL_REASON'], values
            rejected = subprocess.run([*base, *extra, '_cbbh'], env=env, capture_output=True, text=True)
            (args.work/(name+'-failure.log')).write_text(rejected.stdout+rejected.stderr)
            assert rejected.returncode and error in rejected.stdout+rejected.stderr
        else:
            assert not values['PKG_FAIL_REASON'], values
            if native:
                assert not values['EMBERBSD_COMMON_GRAPHICS'] and values['OPSYS'] != 'NetBSD', values
            else:
                assert values['EMBERBSD_COMMON_GRAPHICS']=='yes' and values['OPSYS']=='NetBSD', values
                assert values['TOOLBASE']==str(prefix) and values['CROSS_DESTDIR']==str(target), values
        results[name] = 'refused' if error else 'passed'
        return values

    for arch in ('x86_64', 'aarch64'):
        values = case('default-clang-'+arch, ['CROSS_MACHINE_ARCH='+arch])
        assert values['PKGSRC_COMPILER']=='clang' and values['MACHINE_ARCH']==arch
    gcc = ['EMBERBSD_CROSS_COMPILER_FAMILY=gcc', 'PKGSRC_COMPILER=gcc',
           'USE_NATIVE_GCC=yes', 'USE_PKGSRC_GCC=no', 'USE_PKGSRC_GCC_RUNTIME=no']
    assert case('explicit-gcc', gcc)['PKGSRC_COMPILER']=='gcc'
    case('implicit-gcc', gcc[1:], 'graphics Clang selection')
    case('mixed-family', ['EMBERBSD_CROSS_COMPILER_FAMILY=gcc'], 'explicit graphics GCC selection')
    case('wrong-clang-root', ['CLANGBASE=/unselected'], 'graphics Clang selection')
    case('unknown-family', ['EMBERBSD_CROSS_COMPILER_FAMILY=other'], 'Select clang or gcc')
    for key, value in (('USE_NATIVE_GCC', 'no'), ('USE_PKGSRC_GCC', 'yes'), ('USE_PKGSRC_GCC_RUNTIME', 'yes')):
        case('gcc-'+key.lower(), [word for word in gcc if not word.startswith(key+'=')]+[key+'='+value], 'explicit graphics GCC selection')
    case('mixed-tool-root', ['TOOLDIR=/unselected'], 'common build-tools cross profile')
    case('mixed-sysroot', ['EMBERBSD_CROSS_SYSROOT=/unselected'], 'common build-tools cross profile')
    case('relative-host', ['EMBERBSD_CROSS_HOST_PREFIX=relative'], 'common build-tools cross profile')
    case('missing-opt-in', ['EMBERBSD_COMMON_GRAPHICS_CROSS=no'], 'requires EMBERBSD_COMMON_GRAPHICS_CROSS=yes')
    case('native-recursion', ['USE_CROSS_COMPILE=no'], native=True)
    summary = {'cases': results, 'scope': 'actual pkgsrc profile and failure targets; metadata-only cross inputs, no compiler or target runtime acceptance'}
    (args.work/'result.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
