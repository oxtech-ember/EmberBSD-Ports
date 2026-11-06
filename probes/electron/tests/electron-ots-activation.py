#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Reject foreign OTS GN arguments while permitting verified transitions."""
import importlib.util,json
from pathlib import Path
from types import SimpleNamespace
p=Path(__file__).resolve().parents[3]/'pkgsrc/devel/electron44/files/build-electron.py'
spec=importlib.util.spec_from_file_location('electron',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
selection={'path':'/verified/source','tree_sha256':'a'*64,'receipt_sha256':'b'*64};o=SimpleNamespace(ots_selection=selection)
identity='emberbsd-prepared-source.json';args={'emberbsd_common_ots':True,'emberbsd_ots_identity':'/verified/source/'+identity}
env={'EMBERBSD_OTS_SELECTION':json.dumps(selection,sort_keys=True,separators=(',',':'))}
assert m.ots_activation_args(o,{},env,{},args,identity)==set(args)
assert m.ots_activation_args(o,env,env,args,args,identity)==set()
old={'EMBERBSD_OTS_SELECTION':json.dumps({**selection,'path':'/old'},sort_keys=True,separators=(',',':'))}
assert m.ots_activation_args(o,old,env,{'emberbsd_common_ots':True,'emberbsd_ots_identity':'/old/'+identity},args,identity)=={'emberbsd_ots_identity'}
for oldenv,curenv,oldargs,newargs in (({},env,{'emberbsd_ots_identity':'/foreign'},args),({}, {},{},args),({},env,{}, {**args,'emberbsd_ots_identity':'/foreign'})):
 try:m.ots_activation_args(o,oldenv,curenv,oldargs,newargs,identity)
 except ValueError:pass
 else:raise AssertionError('foreign OTS selection accepted')
print('PASS: OTS activation allows only verified identity transitions')
