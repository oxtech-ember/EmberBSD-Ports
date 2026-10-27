#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check mimalloc source/option/consumer phases with real pkgsrc metadata."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('pkgsrc','bmake','makeconf','shell','patch','distdir'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    recipe=Path(__file__).resolve().parents[1]
    ports=recipe.parents[2]
    with tempfile.TemporaryDirectory(prefix='mimalloc-options-') as temporary:
        root=Path(temporary).resolve();view=root/'pkgsrc';view.mkdir()
        for entry in args.pkgsrc.iterdir():
            if entry.name not in ('devel','mk'):
                (view/entry.name).symlink_to(entry,target_is_directory=entry.is_dir())
        # Patch the option descriptions only in this isolated view.
        (view/'mk/defaults').mkdir(parents=True)
        for entry in (args.pkgsrc/'mk').iterdir():
            if entry.name!='defaults':
                (view/'mk'/entry.name).symlink_to(entry,target_is_directory=entry.is_dir())
        for entry in (args.pkgsrc/'mk/defaults').iterdir():
            if entry.name=='options.description':
                shutil.copyfile(entry,view/'mk/defaults'/entry.name)
            else:
                (view/'mk/defaults'/entry.name).symlink_to(entry,target_is_directory=entry.is_dir())
        (view/'devel').mkdir()
        for entry in (args.pkgsrc/'devel').iterdir():
            if entry.name not in ('mimalloc','mold'):
                (view/'devel'/entry.name).symlink_to(entry,target_is_directory=entry.is_dir())
        shutil.copytree(recipe,view/'devel/mimalloc')
        shutil.copytree(args.pkgsrc/'devel/mold',view/'devel/mold')
        patch=ports/'profiles/common-build-tools/patches/pkgsrc-mimalloc-consumers.patch'
        result=subprocess.run([str(args.patch),'-f','-N','-F0','-p1','-i',str(patch)],cwd=view,text=True,capture_output=True)
        assert result.returncode==0,(result.stdout,result.stderr)
        base=[str(args.bmake),'-m',str(args.bmake.parent.parent/'share/mk'),'SHELL='+str(args.shell),
              'MAKECONF='+str(args.makeconf),'EMBERBSD_DARWIN_BOOTSTRAP=yes','DISTDIR='+str(args.distdir),
              'WRKOBJDIR='+str(root/'objects')]
        count=0
        def run(package,*extra,success=True,native=True):
            nonlocal count
            command=base if native else [part for part in base if not part.startswith('EMBERBSD_DARWIN_BOOTSTRAP=')]
            environment=os.environ.copy()
            if not native:
                environment.pop('EMBERBSD_DARWIN_BOOTSTRAP',None)
            result=subprocess.run([*command,*extra],cwd=view/'devel'/package,text=True,capture_output=True,env=environment)
            assert (result.returncode==0)==success,(package,extra,result.stdout,result.stderr)
            count+=1
            return result.stdout+result.stderr
        for options,expected in (('',('ON','DEFAULT','DEFAULT')),('-malloc-override dynamic-tls generic-arch',('OFF','LOCAL_DYNAMIC','OFF'))):
            extra=[] if not options else ['PKG_OPTIONS.mimalloc='+options]
            flags=run('mimalloc',*extra,'-V','${CMAKE_CONFIGURE_ARGS}')
            for key,value in zip(('OVERRIDE','TLS_MODEL','OPT_ARCH'),expected):
                assert '-DMI_'+key+'='+value in flags,flags
            run('mimalloc',*extra,'EMBER_CARGO_PREFIX=/unconfigured-rust','EMBER_CARGO_HOST_CC=/unconfigured-cc','fetch','checksum')
        vendor=root/'vendor';vendor.mkdir()
        output=run('mimalloc','EMBER_CARGO_PREFIX=/unconfigured-rust',
                   'CARGO_VENDOR_DIR='+str(vendor),'TOOL_PYTHONBIN='+sys.executable,
                   'ember-cargo-configure',success=False)
        assert 'selected rustc must be an absolute executable' in output,output
        cross_makeconf=root/'cross.mk.conf'
        cross_makeconf.write_text('LOCALBASE='+str(args.bmake.parent.parent)+'\nPKGSRC_COMPILER=clang\nPYTHON_VERSION_DEFAULT=315\n')
        output=run('mimalloc','MAKECONF='+str(cross_makeconf),'USE_CROSS_COMPILE=yes',
                   'CROSS_OPSYS=NetBSD','CROSS_OS_VERSION=11.0','CROSS_MACHINE_ARCH=x86_64',
                   'CROSS_OPSYS_VERSION=110000','CROSS_LOWER_OPSYS=netbsd','CROSS_LOWER_OPSYS_VERSUFFIX=',
                   'CROSS_LOWER_VARIANT_VERSION=','CROSS_LOWER_VENDOR=','CROSS_LOWER_OS_VARIANT=',
                   'CROSS_OBJECT_FMT=ELF','do-test',success=False,native=False)
        assert 'do not execute target binaries on the build host' in output,output
        descriptions=run('mimalloc','show-options')
        for description in ('dlopen-compatible local dynamic TLS','generic CPU baseline','process malloc/free entry points'):
            assert description in descriptions,descriptions
        # Exercise the actual pinned Mold recipe with selected-provider metadata.
        # No library or executable is built by this focused phase target.
        run('mold','PKG_BUILD_OPTIONS.mimalloc=malloc-override','ember-mimalloc-consumer-options')
        out=run('mold','PKG_BUILD_OPTIONS.mimalloc=','ember-mimalloc-consumer-options',success=False)
        assert 'requires mimalloc' in out
        # The same public consumer interface expresses an embedding requirement.
        for installed,success in (('',True),('malloc-override',False)):
            run('mold','MIMALLOC_REQUIRE_OVERRIDE=no','PKG_BUILD_OPTIONS.mimalloc='+installed,'ember-mimalloc-consumer-options',success=success)
        for required in ('DYNAMIC_TLS','GENERIC_ARCH'):
            option='dynamic-tls' if required=='DYNAMIC_TLS' else 'generic-arch'
            for installed,success in (('',False),(option,True)):
                run('mold','MIMALLOC_REQUIRE_OVERRIDE=no','MIMALLOC_REQUIRE_'+required+'=yes',
                    'PKG_BUILD_OPTIONS.mimalloc='+installed,'ember-mimalloc-consumer-options',success=success)
        # A mismatched allocator is a configure barrier, not a source policy error.
        run('mold','MIMALLOC_REQUIRE_OVERRIDE=no','PKG_BUILD_OPTIONS.mimalloc=malloc-override','error-check')
        print(f'{count} actual pkgsrc option/source/consumer phase checks passed; no allocator compilation/runtime acceptance.')


if __name__=='__main__':
    main()
