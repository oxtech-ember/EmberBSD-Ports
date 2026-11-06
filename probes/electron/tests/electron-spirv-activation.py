#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check SPIRV activation and selected source/package identity transitions."""
import importlib.util,json
from pathlib import Path
from types import SimpleNamespace
p=Path(__file__).resolve().parents[3]/'pkgsrc/devel/electron44/files/build-electron.py'
spec=importlib.util.spec_from_file_location('electron',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
selection={'path':'/verified/source','tree_sha256':'a'*64,'receipt_sha256':'b'*64};o=SimpleNamespace(shared_spirv_tools=True,spirv_selection=selection)
receipt='emberbsd-prepared-source.json';args={'emberbsd_common_spirv_tools':True,'emberbsd_spirv_source_identity':'/verified/source/'+receipt}
for name in ('spirv_tools','spirv_link','spirv_core'):
 for role in ('host','target'):
  for kind in ('libraries','inputs'):args[f'emberbsd_{name}_{role}_{kind}']=['/verified/'+role+'/'+name+'/'+kind]
for role in ('host','target'):
 args[f'emberbsd_spirv_tools_{role}_table']='/verified/'+role+'/table'
 args[f'emberbsd_spirv_headers_{role}_inputs']=['/verified/'+role+'/headers']
env={'EMBERBSD_SPIRV_SELECTION':json.dumps(selection,sort_keys=True,separators=(',',':'))}
for name in ('TOOLS','HEADERS','LINK','CORE'):env['EMBERBSD_SPIRV_'+name+'_SOURCE_SHA256']='c'*64
assert m.spirv_activation_args(o,{},env,{},args,receipt)==set(args)
assert m.spirv_activation_args(o,env,env,args,args,receipt)==set()
old={**env,'EMBERBSD_SPIRV_SELECTION':json.dumps({**selection,'path':'/old'},sort_keys=True,separators=(',',':'))}
assert m.spirv_activation_args(o,old,env,args,args,receipt)=={'emberbsd_spirv_source_identity'}
for oldenv,curenv,oldargs,newargs in (({},env,{'emberbsd_spirv_source_identity':'/foreign'},args),({}, {},{},args),(env,{**env,'EMBERBSD_SPIRV_HEADERS_SOURCE_SHA256':'d'*64},args,args),({},env,{}, {**args,'emberbsd_spirv_core_target_inputs':[]})):
 try:m.spirv_activation_args(o,oldenv,curenv,oldargs,newargs,receipt)
 except ValueError:pass
 else:raise AssertionError('foreign SPIRV selection accepted')
print('PASS: SPIRV activation requires matching source and role package identities')
