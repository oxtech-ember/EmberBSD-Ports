#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Exercise canonical CRDTP traits with a selected Darwin host toolchain."""
from pathlib import Path
import argparse,os,subprocess
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--toolchain-ninja',type=Path,required=True);p.add_argument('--host-prefix',type=Path,required=True);p.add_argument('--python',type=Path,required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--sdk-source',type=Path,required=True);p.add_argument('--lock-root',type=Path,required=True);a=p.parse_args()
import sys
sys.path.insert(0,str(a.sdk_source/'src'))
from emberbsd_sdk.process import ContextLocks, sanitized_environment
root=a.source.resolve();here=Path(__file__).resolve().parent;work=a.work.resolve();work.mkdir(parents=True,exist_ok=True);h=a.host_prefix.resolve();clang=(h/'bin/clang++').resolve(strict=True); python=a.python.resolve(strict=True)
if not clang.is_relative_to(h) or not python.is_relative_to(h) or not os.access(clang, os.X_OK) or not os.access(python, os.X_OK):
 raise SystemExit('selected clang and Python must be executable within host prefix')
env=sanitized_environment();env['PATH']=str(h/'bin')+':'+str(h/'sbin')
with ContextLocks([str(h)],str(a.lock_root),shared=True), ContextLocks([str(work)],str(a.lock_root)):
    subprocess.run([str(python),str(here/'genflags.py'),'--source',str(root),'--toolchain-ninja',str(a.toolchain_ninja),'--python',str(python),'--output',str(work/'gen')],check=True,env=env)
    incs=['-I'+str(root),'-I'+str(root/'base/allocator/partition_allocator/src'),'-I'+str(work/'gen'),'-I'+str(work/'gen/base/allocator/partition_allocator/src')]
    files={'main':here/'main.cc','protocol_traits':root/'third_party/inspector_protocol/crdtp/chromium/protocol_traits.cc','cbor':root/'third_party/inspector_protocol/crdtp/cbor.cc','protocol_core':root/'third_party/inspector_protocol/crdtp/protocol_core.cc','utf':root/'base/strings/utf_string_conversions.cc','string_util':root/'base/strings/string_util.cc'}
    for name,source in files.items(): subprocess.run([str(clang),'-std=c++23','-ffunction-sections','-fdata-sections',*incs,'-c',str(source),'-o',str(work/(name+'.o'))],check=True,env=env)
    subprocess.run([str(clang),'-Wl,-dead_strip',*[str(work/(name+'.o')) for name in files],'-o',str(work/'test')],check=True,env=env)
    subprocess.run([str(work/'test')],check=True,env=env)
    print('canonical Chromium CRDTP string traits: PASS')
