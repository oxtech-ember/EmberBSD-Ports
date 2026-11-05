#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Only the first verified XML selection may add GN provider inputs."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
p=Path(__file__).resolve().parents[3]/'pkgsrc/devel/electron44/files/build-electron.py'
spec=importlib.util.spec_from_file_location('electron',p); e=importlib.util.module_from_spec(spec); spec.loader.exec_module(e)
o=SimpleNamespace(shared_xml=True); names={'emberbsd_'+p+'_'+r+'_'+k for p in ('xml','xslt') for r in ('host','target') for k in ('library','inputs')}
values={name: ['/selected/input'] if name.endswith('_inputs') else '/selected/lib' for name in names}
env={'EMBERBSD_XML_SOURCE_SHA256':'a'*64}
assert e.xml_activation_args(o,{},env,{},values)==names
assert e.xml_activation_args(o,env,env,values,values)==set()
for old,new in (({next(iter(names)):'/foreign'},values),({}, {**values, next(iter(names)):None})):
    try: e.xml_activation_args(o,{},env,old,new)
    except ValueError: pass
    else: raise AssertionError('unverified XML replacement or missing input accepted')
assert not e.xml_activation_args(o,env,env,values,{**values,next(iter(names)):'/changed'})
print('PASS: first XML selection is additive and later changes remain guarded')
