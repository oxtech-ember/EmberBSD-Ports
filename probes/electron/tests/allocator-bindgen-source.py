#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Compile allocator using GN inputs and check bindgen loader environment."""
import argparse, importlib.util, os, shlex, subprocess, sys, tempfile, types
from pathlib import Path
from unittest import mock
p=argparse.ArgumentParser()
for name in ('source','prepared','gn-out','cxx','git'): p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args(); source=a.source.resolve(strict=True); prepared=a.prepared.resolve(strict=True); out=a.gn_out.resolve(strict=True)
header=Path('base/allocator/partition_allocator/src/partition_alloc/shim')
ninja=out/'obj/base/allocator/partition_allocator/src/partition_alloc/allocator_shim.ninja'
values=dict(line.split(' = ',1) for line in ninja.read_text().splitlines() if ' = ' in line)
flags=sum((shlex.split(values[k]) for k in ('defines','include_dirs','cflags','cflags_cc')),[])
flags=[x for x in flags if x not in ('-Wno-unused-but-set-global','-Wno-deprecated-declarations')]
names=('allocator_shim_internals.h','allocator_shim_override_cpp_symbols.h')
with tempfile.TemporaryDirectory(prefix='electron-allocator-') as t:
 temp=Path(t); base=temp/header; base.mkdir(parents=True)
 for name in names: (base/name).write_bytes(subprocess.check_output([str(a.git),'-C',str(source),'show','HEAD:'+str(header/name)]))
 def compile(root, error):
  inc=root/'base/allocator/partition_allocator/src'
  r=subprocess.run([str(a.cxx),'-I'+str(inc),*flags,'-c',str(source/header/'allocator_shim.cc'),'-o',str(temp/'alloc.o')],cwd=out,capture_output=True,text=True)
  assert (r.returncode != 0 and error in r.stderr) if error else r.returncode == 0, r.stderr
 compile(temp,'exception specification in declaration does not match')
 (base/names[0]).write_bytes((prepared/header/names[0]).read_bytes())
 compile(temp,'missing exception specification')
 compile(prepared,None)
 modules={'action_helpers':types.ModuleType('action_helpers'),'filter_clang_args':types.ModuleType('filter_clang_args')}
 modules['filter_clang_args'].filter_clang_args=lambda args:args
 with mock.patch.dict(sys.modules,modules):
  spec=importlib.util.spec_from_file_location('prepared_bindgen',prepared/'build/rust/gni_impl/run_bindgen.py'); mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
  for platform, expected in (('darwin','DYLD_FALLBACK_LIBRARY_PATH'),('linux','LD_LIBRARY_PATH')):
   calls=[]; output=temp/(platform+'.rs')
   def call(command,**kw):
    calls.append((command,dict(kw.get('env',{}))))
    if len(calls)==1:output.write_text('generated')
   argv=['run_bindgen.py','--bindgen-exe','/fake/bindgen','--rustfmt-exe','/fake/rustfmt','--header','/fake/header','--output',str(output),'--ld-library-path','/test/llvm']
   with mock.patch.object(sys,'argv',argv),mock.patch.object(sys,'platform',platform),mock.patch.object(mod.subprocess,'check_call',side_effect=call),mock.patch.dict(os.environ,{},clear=True):mod.main()
   assert calls[0][1].get(expected)=='/test/llvm' and 'DYLD_LIBRARY_PATH' not in calls[0][1] and len(calls)==2
print('allocator target compile and two causal controls; bindgen Darwin/Linux environment: PASS')
