#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise stage composition using real producer output and base inputs."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

p=argparse.ArgumentParser(description=__doc__)
for name in ('sdk-source','stage','base','pkgsrc-root'): p.add_argument('--'+name,required=True)
a=p.parse_args(); script=Path(__file__).parent.parent / 'files/stage-package.py'; env=dict(os.environ, EMBERBSD_SDK_SOURCE=a.sdk_source)
common=['--stage',a.stage,'--base',a.base,'--pkgsrc-root',a.pkgsrc_root,'--target','amd64']
def call(*args, ok=True):
 r=subprocess.run([os.path.realpath(os.sys.executable),'-B',str(script),*args],env=env,text=True,capture_output=True)
 if (r.returncode==0)!=ok: raise AssertionError(r.stdout+r.stderr)
 return r.stdout.splitlines()
with tempfile.TemporaryDirectory(prefix='llvm-cxx-package-') as tmp:
 seen=set()
 for component in ('libunwind','libcxxabi','libcxx'):
  for role in ('runtime','devel'):
   args=[*common,'--component',component,'--role',role]
   files=call('plist',*args)
   if role == 'runtime':
    assert f'llvm/share/licenses/{component}/LICENSE.TXT' in files
   if component == 'libcxxabi' and role == 'devel':
    assert 'llvm/include/c++/v1/cxxabi.h' in files and 'llvm/include/c++/v1/__cxxabi_config.h' in files
   assert files and not seen.intersection(files), (component,role)
   seen.update(files)
   call('install',*args,'--destdir',tmp)
   for name in files: assert os.path.lexists(Path(tmp)/'usr/pkg'/name)
 for soname in ('libunwind','libc++abi','libc++'):
  assert (Path(tmp)/'usr/pkg/llvm/lib'/(soname+'.so.1')).is_symlink()
 altered=Path(tmp)/'selected-export'
 for rel in ('lang/llvm/version.mk','lang/llvm/distinfo'):
  dest=altered/rel; dest.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(Path(a.pkgsrc_root)/rel,dest)
 for rel in ('lang/compiler-rt/patches','lang/llvm/patches'):
  shutil.copytree(Path(a.pkgsrc_root)/rel,altered/rel)
 patch=altered/'lang/compiler-rt/patches/patch-20-libunwind-library-probes'
 patch.write_text(patch.read_text()+'\n# altered selected export\n')
 mismatch=common.copy(); mismatch[mismatch.index(a.pkgsrc_root)]=str(altered)
 call('plist',*mismatch,'--component','libcxx','--role','runtime',ok=False)
 wrong=common.copy(); wrong[wrong.index('amd64')]='aarch64'
 call('plist',*wrong,'--component','libcxx','--role','runtime',ok=False)
 broken=Path(tmp)/'broken-stage'; shutil.copytree(a.stage,broken,symlinks=True)
 with (broken/'usr/pkg/llvm/lib/libc++.so.1.0').open('ab') as f: f.write(b'corruption')
 bad=common.copy();bad[bad.index(a.stage)]=str(broken)
 call('plist',*bad,'--component','libcxx','--role','runtime',ok=False)
print('PASS: actual stage roles, unique ownership, SONAME links, target and corruption refusals')
