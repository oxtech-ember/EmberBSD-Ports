#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Allow only a first verified provider addition, never replacement."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
p=Path(__file__).resolve().parents[3]/'pkgsrc/devel/electron44/files/build-electron.py'
spec=importlib.util.spec_from_file_location('electron',p); e=importlib.util.module_from_spec(spec); spec.loader.exec_module(e)
o=SimpleNamespace(shared_font=True)
keys={'emberbsd_'+p+'_'+r+'_'+k for p in ('freetype','harfbuzz') for r in ('host','target') for k in ('libraries','inputs')}
keys.update(('emberbsd_common_font','use_system_freetype','use_system_harfbuzz'))
values={key:True if key in ('emberbsd_common_font','use_system_freetype','use_system_harfbuzz') else ['/verified/'+key] for key in keys}; env={'EMBERBSD_FONT_SOURCE_SHA256':'a'*64}
assert e.font_activation_args(o,{},env,{},values)==keys
assert e.font_activation_args(o,env,env,values,values)==set()
for old,new in (({next(iter(keys)):['/foreign']},values), ({}, {**values, next(iter(keys)):[]})):
    try: e.font_activation_args(o,{},env,old,new)
    except ValueError: pass
    else: raise AssertionError('unverified replacement or incomplete selection accepted')
# A changed previously selected argument is not exempt from the normal identity check.
changed={**values, 'emberbsd_freetype_host_libraries':['/other']}
allowed=e.font_activation_args(o,env,env,values,changed)
assert not allowed and any(values[k]!=changed[k] for k in keys)
print('PASS: first font activation is additive; later changes remain guarded')
