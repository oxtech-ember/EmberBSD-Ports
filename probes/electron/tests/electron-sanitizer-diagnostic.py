#!/usr/bin/env python3
"""Check target package validation and compile/link binding boundaries."""
import argparse, copy, importlib.util, os, shutil, sys, tempfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--sdk-source',type=Path,required=True);p.add_argument('--package',type=Path,required=True);p.add_argument('--resource',type=Path,required=True);p.add_argument('--sha256',required=True);p.add_argument('--llvm-version',required=True);p.add_argument('--owner',type=Path,required=True);a=p.parse_args()
sys.path.insert(0,str(a.sdk_source/'src'))
from emberbsd_sdk import binary_release, package_updates, elf, compiler_bindings, paths
spec=importlib.util.spec_from_file_location('sanitizer',a.owner/'sanitizer-diagnostic.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
pkg=a.package;resource=a.resource;sha=a.sha256;sdk={'binary_release':binary_release,'package_updates':package_updates,'elf':elf,'paths':paths}
assert m.verify(pkg,sha,resource,sdk,version=a.llvm_version,target='amd64')[0]==resource
try:m.verify(pkg,'0'*64,resource,sdk,version=a.llvm_version,target='amd64');raise AssertionError('bad digest accepted')
except ValueError:pass
with tempfile.TemporaryDirectory() as td:
 fake=Path(td)/a.llvm_version.split('.')[0];shutil.copytree(resource,fake)
 def reject():
  try:m.verify(pkg,sha,fake,sdk,version=a.llvm_version,target='amd64');raise AssertionError('changed stage accepted')
  except ValueError:pass
 header=fake/'include/sanitizer/asan_interface.h';original=header.read_bytes();header.write_text('changed');reject();header.write_bytes(original)
 builtins=fake/'lib/netbsd/libclang_rt.builtins-x86_64.a';original=builtins.read_bytes();builtins.write_bytes(original+b'bad');reject();builtins.write_bytes(original)
 extra=fake/'include/stddef.h';extra.write_text('foreign');reject();extra.unlink()
 (fake/'include/escape').symlink_to(header);reject();(fake/'include/escape').unlink()
 (fake/'include/extra-empty').mkdir();reject()
base={'format':'emberbsd-compiler-binding','version':1,'commands':{k:['/selected/clang','--target=x86_64--netbsd','--sysroot=/target','-resource-dir=/target/llvm','-nobuiltininc','-isystem','/selected/lib/clang/23/include'] for k in ('cc','cxx','cpp')},'flags':{k:[] for k in ('cppflags','cflags','cxxflags','ldflags')},'link_flags':{'cc':['--ld-path=/selected/ld','--rtlib=compiler-rt','--unwindlib=none'],'cxx':['--ld-path=/selected/ld','--rtlib=compiler-rt','--unwindlib=none','-stdlib=libc++']}}
old=copy.deepcopy(base);m.bind(base,resource,'/selected/lib/clang/23/include');compile=compiler_bindings.compiler_argv(base,'cc',['-c','x.c']);link=compiler_bindings.compiler_argv(base,'cc',['x.c','-o','x']);assert '-resource-dir='+str(resource) not in compile and link[-1]=='-resource-dir='+str(resource);assert old['link_flags']['cc']==base['link_flags']['cc'][:-1];assert str(resource/'include') in compile;print('PASS: actual package identity/architecture/stage mismatch; SDK compile vs link boundary')
