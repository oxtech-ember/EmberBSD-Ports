#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Exercise Rollup source/metadata and ESTree data installation in real pkgsrc."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('pkgsrc','bmake','makeconf','shell','distdir'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    recipe=Path(__file__).resolve().parents[1];ports=recipe.parents[2]
    with tempfile.TemporaryDirectory(prefix='rollup-pkgsrc-') as temporary:
        root=Path(temporary).resolve();view=root/'pkgsrc'
        def directory(relative,own):
            source=args.pkgsrc/relative;destination=view/relative;destination.mkdir(parents=True)
            for entry in source.iterdir():
                if entry.name not in own:
                    (destination/entry.name).symlink_to(entry,target_is_directory=entry.is_dir())
        packages=('rollup','mimalloc','node-types-estree')
        directory('',{'devel','lang'});directory('devel',set(packages));directory('lang',{'rust'})
        directory('lang/rust',{'emberbsd-cargo.mk','emberbsd-cargo-config.py'})
        for package in packages:shutil.copytree(ports/'pkgsrc/devel'/package,view/'devel'/package)
        for source,destination in (('cargo.mk','emberbsd-cargo.mk'),('cargo-config.py','emberbsd-cargo-config.py')):
            shutil.copyfile(ports/'profiles/common-build-tools'/source,view/'lang/rust'/destination)
        base=[str(args.bmake),'-m',str(args.bmake.parent.parent/'share/mk'),'SHELL='+str(args.shell),
              'MAKECONF='+str(args.makeconf),'EMBERBSD_DARWIN_BOOTSTRAP=yes','DISTDIR='+str(args.distdir),
              'WRKOBJDIR='+str(root/'objects')]
        count=0
        def run(package,*extra,native=True,success=True):
            nonlocal count
            command=base if native else [word for word in base if not word.startswith('EMBERBSD_DARWIN_BOOTSTRAP=')]
            env=os.environ.copy()
            if not native:env.pop('EMBERBSD_DARWIN_BOOTSTRAP',None)
            result=subprocess.run([*command,*extra],cwd=view/'devel'/package,text=True,capture_output=True,env=env)
            assert (result.returncode==0)==success,(package,extra,result.stdout,result.stderr)
            count+=1
            return result.stdout.strip()
        run('rollup','fetch','checksum')
        tools=run('rollup','-V','${TOOL_DEPENDS}');build=run('rollup','-V','${BUILD_DEPENDS}')
        runtime=run('rollup','-V','${DEPENDS}')
        assert 'rust-bin>=' in tools and 'python315' in tools,tools
        assert 'rust-bin' not in build,build
        assert all(name in runtime for name in ('mimalloc>=3.6.0','node-types-estree>=1.0.9','nodejs>=24.22.1')),runtime
        native_target=run('rollup','-V','${EMBER_CARGO_TARGET}');native_base=run('rollup','-V','${ROLLUP_NAPI_BASE}')
        assert native_target in ('aarch64-apple-darwin','x86_64-apple-darwin'),native_target
        assert native_base in ('darwin-arm64','darwin-x64'),native_base
        # A native bootstrap profile is not a cross profile. Use a metadata-only
        # cross fixture to check the declared package defaults without compiling.
        cross_config=root/'cross-fixture.mk.conf'
        cross_config.write_text('LOCALBASE='+str(args.bmake.parent.parent)+'\nPYTHON_VERSION_DEFAULT=315\nPKGSRC_COMPILER=clang\n')
        cross=['MAKECONF='+str(cross_config),'USE_CROSS_COMPILE=yes','CROSS_OPSYS=NetBSD','CROSS_OS_VERSION=11.0',
               'CROSS_OPSYS_VERSION=110000','CROSS_LOWER_OPSYS=netbsd','CROSS_LOWER_OPSYS_VERSUFFIX=',
               'CROSS_LOWER_VARIANT_VERSION=','CROSS_LOWER_VENDOR=','CROSS_LOWER_OS_VARIANT=','CROSS_OBJECT_FMT=ELF']
        for arch,rust,node in (('aarch64','aarch64-unknown-netbsd','netbsd-arm64'),('x86_64','x86_64-unknown-netbsd','netbsd-x64')):
            output=run('rollup',*cross,'CROSS_MACHINE_ARCH='+arch,'-V','${EMBER_CARGO_TARGET}','-V','${ROLLUP_NAPI_BASE}',native=False)
            assert output.splitlines()==[rust,node],output
            required=run('rollup',*cross,'CROSS_MACHINE_ARCH='+arch,'-V','${MIMALLOC_REQUIRE_OVERRIDE}','-V','${MIMALLOC_REQUIRE_DYNAMIC_TLS}','-V','${MIMALLOC_REQUIRE_GENERIC_ARCH:Uno}',native=False)
            assert required.splitlines()==['no','yes','yes' if arch=='aarch64' else 'no'],required
        # Source acquisition still passes with a provider mode configure rejects.
        run('rollup','PKG_BUILD_OPTIONS.mimalloc=malloc-override','fetch','checksum')
        run('rollup','PKG_BUILD_OPTIONS.mimalloc=malloc-override','ember-mimalloc-consumer-options',success=False)
        run('node-types-estree','fetch','checksum')
        extract=root/'estree-source';extract.mkdir()
        with tarfile.open(args.distdir/'estree-1.0.9.tgz') as archive:archive.extractall(extract,filter='data')
        package_prefix=Path(run('node-types-estree','-V','${PREFIX}'))
        stage=root/'stage'
        directories=run('node-types-estree','-V','${INSTALLATION_DIRS}').split()
        for relative in directories:(stage/package_prefix.relative_to('/')/relative).mkdir(parents=True,exist_ok=True)
        run('node-types-estree','WRKSRC='+str(extract/'estree'),'DESTDIR='+str(stage),'do-install')
        installed=stage/package_prefix.relative_to('/')/'lib/node_modules/@types/estree'
        for name in ('LICENSE','README.md','flow.d.ts','index.d.ts','package.json'):
            assert (installed/name).read_bytes()==(extract/'estree'/name).read_bytes(),name
        assert json.loads((installed/'package.json').read_text())['version']=='1.0.9'
        print(json.dumps({'pkgsrc_checks':count,'estree_payload_files':5,'scope':'actual source/checksum, native/cross metadata and data-only staged install; no Rust/C/C++ build or target execution'}))


if __name__=='__main__':
    main()
