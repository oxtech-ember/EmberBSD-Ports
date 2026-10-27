#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Exercise the exported Cargo include in real pkgsrc without compiling crates."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('pkgsrc','bmake','makeconf','shell'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    owner=Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix='cargo-pkgsrc-') as temporary:
        root=Path(temporary).resolve()
        view=root/'pkgsrc'
        # Only this view's test recipe and lang/rust are writable. Other
        # framework files are references to the supplied completed export.
        def directory(relative, own):
            source=args.pkgsrc/relative
            destination=view/relative
            destination.mkdir(parents=True)
            for entry in source.iterdir():
                if entry.name not in own:
                    (destination/entry.name).symlink_to(entry, target_is_directory=entry.is_dir())
        directory('',{'devel','lang'})
        directory('devel',{'cargo-routing-fixture'})
        directory('lang',{'rust'})
        directory('lang/rust',{'emberbsd-cargo.mk','emberbsd-cargo-config.py'})
        shutil.copyfile(owner/'cargo.mk',view/'lang/rust/emberbsd-cargo.mk')
        shutil.copyfile(owner/'cargo-config.py',view/'lang/rust/emberbsd-cargo-config.py')
        port=view/'devel/cargo-routing-fixture';port.mkdir()
        (port/'DESCR').write_text('Source and configure routing fixture.\n')
        (port/'PLIST').write_text('@comment fixture\n')
        (port/'Makefile').write_text('''DISTNAME= cargo-routing-1.0
CATEGORIES= devel
MASTER_SITES=
EXTRACT_SUFX= .tar
LICENSE= 2-clause-bsd
COMMENT= Cargo tool-routing fixture
USE_LANGUAGES= c c++
RUST_REQ= 1.99.1
.include "../../lang/rust/emberbsd-cargo.mk"
.include "../../mk/bsd.pkg.mk"
''')
        cache=root/'cache';cache.mkdir()
        archive=cache/'cargo-routing-1.0.tar'
        with tarfile.open(archive,'w') as tar:
            content=b'[package]\nname="cargo-routing"\nversion="1.0.0"\n'
            entry=tarfile.TarInfo('cargo-routing-1.0/Cargo.toml');entry.size=len(content)
            tar.addfile(entry,io.BytesIO(content))
        data=archive.read_bytes()
        (port/'distinfo').write_text('$NetBSD$\n\n'+''.join(f'{name} ({archive.name}) = {digest}\n' for name,digest in (('BLAKE2s',hashlib.blake2s(data).hexdigest()),('SHA512',hashlib.sha512(data).hexdigest()),('Size',str(len(data))+' bytes'))))
        prefix=root/'selected-host';(prefix/'bin').mkdir(parents=True)
        for name in ('rustc','clang','clang++','llvm-ar','cargo'):
            path=prefix/'bin'/name
            if name=='rustc':
                code='print("host: aarch64-apple-darwin")'
            elif name=='cargo':
                # Observe the actual runner after do-cargo-build changes cwd.
                code='import json, os, pathlib, sys\npathlib.Path('+repr(str(root/'cargo-run.json'))+').write_text(json.dumps({"argv": sys.argv[1:], "cwd": os.getcwd()}))'
            else:
                code='raise SystemExit("fixture must not compile")'
            path.write_text('#!'+sys.executable+'\n'+code+'\n');path.chmod(0o755)
        base=[str(args.bmake),'-m',str(args.bmake.parent.parent/'share/mk'),'SHELL='+str(args.shell),'MAKECONF='+str(args.makeconf),'WRKOBJDIR='+str(root/'objects'),'DISTDIR='+str(cache),'EMBERBSD_DARWIN_BOOTSTRAP=yes','MAKE_JOBS=2']
        def run(*extra, success=True, native=True):
            command=base if native else [item for item in base if not item.startswith('EMBERBSD_DARWIN_BOOTSTRAP=')]
            environment=os.environ.copy()
            if not native:
                environment.pop('EMBERBSD_DARWIN_BOOTSTRAP',None)
            result=subprocess.run([*command,*extra],cwd=port,text=True,capture_output=True,env=environment)
            if (result.returncode==0)!=success:
                raise AssertionError('bmake fixture failed\n'+shlex.join(extra)+'\n'+result.stdout+result.stderr)
            return result.stdout
        # Fetch/checksum must not depend on a runnable Rust or C toolchain.
        run('fetch','checksum')
        tools=run('-V','${TOOL_DEPENDS}');build=run('-V','${BUILD_DEPENDS}')
        assert 'rust-bin>=' in tools and 'python315' in tools,tools
        assert 'rust-bin' not in build,build
        vendor=root/'vendor';vendor.mkdir()
        config=root/'native/config.toml'
        selected=['EMBER_CARGO_PREFIX='+str(prefix),'TOOL_PYTHONBIN='+sys.executable,
                  'CARGO_VENDOR_DIR='+str(vendor),'EMBER_CARGO_CONFIG='+str(config),'EMBER_CARGO_OUTPUT='+str(root/'out'),
                  'EMBER_CARGO_HOST_CC='+str(prefix/'bin/clang')+' -arch arm64',
                  'EMBER_CARGO_HOST_CXX='+str(prefix/'bin/clang++'),
                  'EMBER_CARGO_HOST_AR='+str(prefix/'bin/llvm-ar'),
                  'EMBER_CARGO_HOST_CFLAGS=-DHOST_ONLY','EMBER_CARGO_HOST_LDFLAGS=-L/host',
                  'RUSTFLAGS=-C opt-level=2']
        run(*selected,'ember-cargo-configure')
        native=tomllib.loads(config.read_text())
        assert native['build']['target']=='aarch64-apple-darwin'
        assert native['env']['CFLAGS']['value']=='-DHOST_ONLY'
        crate_source=root/'source'/'nested-crate'
        crate_source.mkdir(parents=True)
        run(*selected,'CARGO_WRKSRC='+str(crate_source),'CARGO_ARGS=metadata --offline','do-cargo-build')
        observed=json.loads((root/'cargo-run.json').read_text())
        assert observed=={'argv':['--config',str(config),'metadata','--offline'],
                          'cwd':str(crate_source)},observed
        target='x86_64-unknown-netbsd'
        cross_config=root/'cross/config.toml'
        # The supplied native bootstrap policy correctly refuses cross builds.
        # A minimal fixture MAKECONF tests generic pkgsrc routing only; a real
        # target SDK/profile is intentionally not qualified by this test.
        cross_makeconf=root/'cross-fixture.mk.conf'
        cross_makeconf.write_text('LOCALBASE='+str(args.bmake.parent.parent)+'\nPYTHON_VERSION_DEFAULT=315\nPKGSRC_COMPILER=clang\n')
        cross=[item for item in selected if not item.startswith('EMBER_CARGO_CONFIG=')]
        cross.append('MAKECONF='+str(cross_makeconf))
        cross.extend(['USE_CROSS_COMPILE=yes','CROSS_OPSYS=NetBSD','CROSS_OS_VERSION=11.0','CROSS_MACHINE_ARCH=x86_64',
                      'CROSS_OPSYS_VERSION=110000','CROSS_LOWER_OPSYS=netbsd','CROSS_LOWER_OPSYS_VERSUFFIX=',
                      'CROSS_LOWER_VARIANT_VERSION=','CROSS_LOWER_VENDOR=','CROSS_LOWER_OS_VARIANT=','CROSS_OBJECT_FMT=ELF',
                      'EMBER_CARGO_CONFIG='+str(cross_config),'EMBER_CARGO_TARGET='+target,
                      'CC='+str(prefix/'bin/clang')+' --target=x86_64--netbsd',
                      'CXX='+str(prefix/'bin/clang++')+' --target=x86_64--netbsd','AR='+str(prefix/'bin/llvm-ar'),
                      'CFLAGS=-DTARGET_ONLY','CPPFLAGS=--sysroot=/target','LDFLAGS=-L/target'])
        run(*cross,'ember-cargo-configure',native=False)
        result=tomllib.loads(cross_config.read_text())
        assert result['build']['target']==target
        assert result['env']['CFLAGS']['value']=='-DHOST_ONLY'
        assert result['env']['CFLAGS_'+target]['value']=='-DTARGET_ONLY'
        assert result['env']['CPPFLAGS_'+target]['value']==''
        assert '--sysroot=/target' in Path(result['env']['CC_'+target]['value']).read_text()
        host_linker=Path(result['target']['aarch64-apple-darwin']['linker']).read_text()
        target_linker=Path(result['target'][target]['linker']).read_text()
        assert '-arch arm64' in host_linker and '-L/host' in host_linker and '/target' not in host_linker
        assert '--target=x86_64--netbsd' in target_linker and '-L/target' in target_linker and '-L/host' not in target_linker
        run(*selected,'RUST_TYPE=bin','ember-cargo-configure',success=False)
        print(json.dumps({'fetch_checksum':'pass','native_tool_dependencies':'pass','native_configure':'pass','runner_after_chdir':'pass','cross_configure':'pass','wrong_rust_role_rejected':'pass','scope':'pkgsrc configure and runner execution with observed Cargo stub; no compilation'}))


if __name__=='__main__':
    main()
