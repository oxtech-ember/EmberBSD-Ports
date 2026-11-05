#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Only disabling the three optional SwiftShader switches may migrate."""
import importlib.util
from pathlib import Path
owner=Path(__file__).resolve().parents[3]/'pkgsrc/devel/electron44/files/build-electron.py'
spec=importlib.util.spec_from_file_location('electron',owner); m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
keys=('enable_swiftshader','enable_swiftshader_vulkan','angle_enable_swiftshader')
new={key:False for key in keys}
assert m.verified_swiftshader_disable({},new)==set(keys)
assert m.verified_swiftshader_disable(new,new)==set()
assert m.verified_swiftshader_disable(dict(new,enable_swiftshader=True),new)=={'enable_swiftshader'}
for old,bad in (({},dict(new,angle_enable_swiftshader=True)),({'enable_swiftshader':'foreign'},new)):
    try: m.verified_swiftshader_disable(old,bad)
    except ValueError: pass
    else: raise AssertionError('invalid renderer transition accepted')
print('PASS: SwiftShader policy permits only explicit disabling')
