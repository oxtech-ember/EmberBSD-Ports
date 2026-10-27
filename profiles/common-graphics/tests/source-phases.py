#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Run actual graphics fetch/checksum and missing-build-input refusals."""
import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('pkgsrc', 'host-prefix', 'utility-path', 'distdir', 'work'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    if any(not value.is_absolute() for value in vars(args).values()) or args.work.exists():
        parser.error('use absolute inputs and a new work directory')
    for name in ('mesa-26.2.5.tar.xz','wayland-protocols-1.49.tar.xz'):
        if not (args.distdir/name).is_file():
            parser.error('cache the recipe-pinned archive first: '+name)
    args.work.mkdir()
    owner = Path(__file__).resolve().parents[3]
    tree = args.work/'pkgsrc';tree.mkdir()
    for entry in args.pkgsrc.iterdir():
        if entry.name not in ('graphics','devel','EMBERBSD-COMMON-GRAPHICS-MK.CONF'):
            (tree/entry.name).symlink_to(entry.resolve(),target_is_directory=entry.is_dir())
    for category, changed in (('graphics',{'MesaLib'}),('devel',{'wayland','wayland-protocols'})):
        (tree/category).mkdir()
        for entry in (args.pkgsrc/category).iterdir():
            if entry.name not in changed:
                (tree/category/entry.name).symlink_to(entry.resolve(),target_is_directory=entry.is_dir())
        for name in changed:
            shutil.copytree(owner/'pkgsrc'/category/name,tree/category/name)
    shutil.copyfile(owner/'profiles/common-graphics/mk.conf',tree/'EMBERBSD-COMMON-GRAPHICS-MK.CONF')
    target = args.work/'metadata-only-target';(target/'usr/include').mkdir(parents=True)
    (target/'usr/include/stddef.h').write_text('#error source-phase fixture must not compile\n')
    prefix = args.host_prefix
    config = args.work/'mk.conf'
    config.write_text('''
LOCALBASE=@PREFIX@
PYTHON_VERSION_DEFAULT=315
PKGSRC_COMPILER=clang
PKG_TOOLS_BIN=@PREFIX@/sbin
NATIVE_PKG_TOOLS_BIN=@PREFIX@/sbin
USE_CROSS_COMPILE=yes
CROSS_OPSYS=NetBSD
CROSS_OS_VERSION=11.0
CROSS_MACHINE_ARCH=x86_64
CROSS_OPSYS_VERSION=110000
CROSS_LOWER_OPSYS=netbsd
CROSS_LOWER_OPSYS_VERSUFFIX=
CROSS_LOWER_VARIANT_VERSION=
CROSS_LOWER_VENDOR=
CROSS_LOWER_OS_VARIANT=
CROSS_OBJECT_FMT=ELF
CROSS_LOCALBASE=/usr/pkg
CROSS_DESTDIR=@TARGET@
TOOLDIR=@PREFIX@
CLANGBASE=@PREFIX@
EMBERBSD_CROSS_TOOLS=@PREFIX@
EMBERBSD_CROSS_SYSROOT=@TARGET@
EMBERBSD_CROSS_HOST_PREFIX=@PREFIX@
EMBERBSD_COMMON_GRAPHICS_CROSS=yes
.if defined(BSD_PKG_MK)
.include "@TREE@/EMBERBSD-COMMON-GRAPHICS-MK.CONF"
.endif
'''.replace('@PREFIX@',str(prefix)).replace('@TARGET@',str(target)).replace('@TREE@',str(tree)))
    # This is metadata-only input plumbing through the real profile. It neither
    # creates a target SDK nor invents an LLVM metadata receipt. Only source
    # checks and immediate consuming-phase failures are executed.
    environment = dict(os.environ,PATH=str(args.utility_path),TMPDIR=str(args.work))
    for name in ('EMBERBSD_DARWIN_BOOTSTRAP','EMBERBSD_GRAPHICS_LLVM_CONFIG',
                 'EMBERBSD_WAYLAND_SCANNER','EMBERBSD_SDK_SOURCE','EMBERBSD_MESA_GENERATORS'):
        environment.pop(name,None)
    base=[str(prefix/'bin/bmake'),'-m',str(prefix/'share/mk'),'SHELL='+str(prefix/'bin/mksh'),
          'MAKECONF='+str(config),'WRKOBJDIR='+str(args.work/'objects'),'DISTDIR='+str(args.distdir)]
    checks={}

    def run(name,package,extra,expected=None):
        command=[*base,'-C',str(tree/package),*extra]
        result=subprocess.run(command,env=environment,capture_output=True,text=True)
        output=result.stdout+result.stderr
        (args.work/(name+'.log')).write_text(shlex.join(command)+'\n'+output)
        if expected:
            assert result.returncode and expected in output, name+'\n'+output
        else:
            assert not result.returncode, name+'\n'+output
        checks[name]='refused' if expected else 'passed'
        return result.stdout

    for package in ('graphics/MesaLib','devel/wayland-protocols'):
        name=Path(package).name
        tools=run(name+'-source-tools',package,['-V','${NATIVE_PKG_INFO_CMD}','-V','${PKGTOOLS_VERSION}'])
        assert str(prefix/'sbin/pkg_info') in tools and '20010302' not in tools
        failure=run(name+'-metadata',package,['-V','${PKG_FAIL_REASON}'])
        assert not failure.strip(),failure
        run(name+'-fetch-checksum',package,['fetch','checksum'])
    run('MesaLib-missing-llvm','graphics/MesaLib',['pre-configure'],
        'requires EMBERBSD_GRAPHICS_LLVM_CONFIG')
    run('MesaLib-relative-llvm','graphics/MesaLib',
        ['EMBERBSD_GRAPHICS_LLVM_CONFIG=relative/llvm-config','pre-configure'],
        'absolute receipt-guarded llvm-config')
    run('MesaLib-unprepared-llvm','graphics/MesaLib',
        ['EMBERBSD_GRAPHICS_LLVM_CONFIG='+str(prefix/'bin/llvm-config'),'pre-configure'],
        'absolute receipt-guarded llvm-config')
    # Preserve earlier MAKECONF choices, including defined-empty. No receipt
    # is fabricated: conflicts must fail before inspecting helper artifacts.
    for name, value in (('earlier-llvm', '/usr/bin/false'), ('earlier-empty-llvm', '')):
        earlier=args.work/(name+'.mk.conf')
        earlier.write_text('LLVM_CONFIG_PATH='+value+'\n.include "'+str(config)+'"\n')
        overrides=['MAKECONF='+str(earlier),
                   'EMBERBSD_GRAPHICS_LLVM_CONFIG='+str(prefix/'bin/llvm-config')]
        run(name+'-fetch','graphics/MesaLib',[*overrides,'fetch','checksum'])
        run(name+'-configure','graphics/MesaLib',[*overrides,'pre-configure'],
            'earlier conflicting LLVM_CONFIG_PATH')
    run('command-line-llvm','graphics/MesaLib',
        ['EMBERBSD_GRAPHICS_LLVM_CONFIG='+str(prefix/'bin/llvm-config'),
         'LLVM_CONFIG_PATH=/usr/bin/false','pre-configure'], 'overridden LLVM_CONFIG_PATH')
    run('protocols-missing-scanner','devel/wayland-protocols',['pre-configure'],
        'require EMBERBSD_WAYLAND_SCANNER')
    run('MesaLib-missing-generators','graphics/MesaLib',['emberbsd-mesa-generators-check'],
        'requires an absolute sealed EMBERBSD_MESA_GENERATORS')
    # License and source integrity remain ordinary framework checks.
    run('MesaLib-license','graphics/MesaLib',['LICENSE=source-phase-unaccepted-license','fetch'],
        'license')
    corrupt=args.work/'corrupt-cache';corrupt.mkdir()
    shutil.copyfile(args.distdir/'wayland-protocols-1.49.tar.xz',corrupt/'wayland-protocols-1.49.tar.xz')
    with (corrupt/'wayland-protocols-1.49.tar.xz').open('ab') as stream:stream.write(b'changed')
    run('protocols-corrupt','devel/wayland-protocols',['DISTDIR='+str(corrupt),'checksum'],
        'Checksum')
    summary={'actual_pkgsrc_cases':checks,
             'scope':'cached source fetch/checksum and consuming-phase refusals; metadata-only target, no target compile or fabricated LLVM receipt'}
    (args.work/'result.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary))


if __name__=='__main__':
    main()
