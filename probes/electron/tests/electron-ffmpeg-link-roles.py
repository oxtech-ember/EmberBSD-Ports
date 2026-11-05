#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check explicit provider paths in native load and NetBSD ELF links."""
import argparse
import ctypes
from pathlib import Path
import subprocess
import tempfile
p=argparse.ArgumentParser(description=__doc__)
for role in ('clang','ld64','lld','readelf','otool'): p.add_argument('--'+role,type=Path,required=True)
a=p.parse_args()
def run(*cmd): return subprocess.run([str(x) for x in cmd],check=True,capture_output=True,text=True).stdout
with tempfile.TemporaryDirectory(prefix='ffmpeg-link-roles-') as tmp:
    root=Path(tmp).resolve(); (root/'lib').mkdir()
    source=root/'provider.c'; source.write_text('int ffmpeg_fixture(void) { return 42; }\n')
    consumer=root/'consumer.c'; consumer.write_text('extern int ffmpeg_fixture(void); int consumer(void) { return ffmpeg_fixture(); }\n')
    obj=root/'host.o'; dylib=root/'lib/libfixture.dylib'; app=root/'consumer.dylib'
    run(a.clang,'--target=arm64-apple-macos15','-c',source,'-o',obj)
    run(a.ld64,'-dylib','-arch','arm64','-platform_version','macos','15.0','15.0','-install_name','@rpath/libfixture.dylib','-o',dylib,obj)
    run(a.clang,'--target=arm64-apple-macos15','-c',consumer,'-o',root/'host-consumer.o')
    run(a.ld64,'-dylib','-arch','arm64','-platform_version','macos','15.0','15.0','-o',app,root/'host-consumer.o',dylib,'-rpath',root/'lib')
    assert '@rpath/libfixture.dylib' in run(a.otool,'-L',app)
    assert str(root/'lib') in run(a.otool,'-l',app)
    lib=ctypes.CDLL(str(app)); assert lib.consumer()==42
    run(a.clang,'--target=x86_64-unknown-netbsd','-fPIC','-c',source,'-o',root/'target.o')
    run(a.lld,'-shared','-soname','libfixture.so.1','-o',root/'lib/libfixture.so',root/'target.o')
    run(a.clang,'--target=x86_64-unknown-netbsd','-fPIC','-c',consumer,'-o',root/'target-consumer.o')
    result=root/'target.so'
    run(a.lld,'-shared','-o',result,root/'target-consumer.o',root/'lib/libfixture.so','-rpath','/usr/pkg/lib/ffmpeg9')
    dynamic=run(a.readelf,'-d',result)
    assert 'libfixture.so.1' in dynamic and '/usr/pkg/lib/ffmpeg9' in dynamic
print('PASS: native explicit install name/load and target ELF SONAME/runtime path')
