#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Allow only a first verified provider addition, never replacement."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
p=Path(__file__).resolve().parents[3]/'pkgsrc/devel/electron44/files/build-electron.py'
spec=importlib.util.spec_from_file_location('electron',p); e=importlib.util.module_from_spec(spec); spec.loader.exec_module(e)
o=SimpleNamespace(shared_woff2=True)
keys={'emberbsd_'+p+'_'+r+'_'+k for p in ('woff2',) for r in ('host','target') for k in ('libraries','inputs')}
keys.add('emberbsd_common_woff2')
selection_keys = keys
values={key:True if key == 'emberbsd_common_woff2' else ['/verified/'+key] for key in keys}; env={'EMBERBSD_WOFF2_SOURCE_SHA256':'a'*64}
assert e.woff2_activation_args(o,{},env,{},values)==selection_keys
assert e.woff2_activation_args(o,env,env,values,values)==set()
for old,new in (({next(iter(keys)):['/foreign']},values), ({}, {**values, next(iter(keys)):[]})):
    try: e.woff2_activation_args(o,{},env,old,new)
    except ValueError: pass
    else: raise AssertionError('unverified replacement or incomplete selection accepted')
# A changed previously selected argument is not exempt from the normal identity check.
changed={**values, 'emberbsd_woff2_host_libraries':['/other']}
allowed=e.woff2_activation_args(o,env,env,values,changed)
assert not allowed and any(values[k]!=changed[k] for k in keys)
print('PASS: first codec activation is additive; later changes remain guarded')
