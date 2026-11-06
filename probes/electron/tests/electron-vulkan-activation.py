#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check first Vulkan activation is additive and later identity remains strict."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
p = Path(__file__).resolve().parents[3] / 'pkgsrc/devel/electron44/files/build-electron.py'
spec = importlib.util.spec_from_file_location('electron', p)
e = importlib.util.module_from_spec(spec); spec.loader.exec_module(e)
o = SimpleNamespace(shared_vulkan=True)
keys = {'emberbsd_vulkan_' + role + '_' + kind for role in ('host', 'target') for kind in ('library', 'inputs', 'runtime_dir')}
keys.update('emberbsd_vulkan_headers_' + role + '_' + kind for role in ('host', 'target') for kind in ('include', 'inputs'))
keys.add('emberbsd_common_vulkan')
values = {key: True if key == 'emberbsd_common_vulkan' else ['/verified/' + key] for key in keys}
values['angle_use_custom_libvulkan'] = False
environment = {'EMBERBSD_VULKAN_SOURCE_SHA256': 'a' * 64}
for old in ({}, {'angle_use_custom_libvulkan': True}, {'angle_use_custom_libvulkan': False}):
    assert e.vulkan_activation_args(o, {}, environment, old, values) == keys | {'angle_use_custom_libvulkan'}
assert e.vulkan_activation_args(o, environment, environment, values, values) == set()
for old, new in (({'angle_use_custom_libvulkan': 'foreign'}, values),
                 ({next(iter(keys)): ['/foreign']}, values), ({}, {**values, next(iter(keys)): []}),
                 ({}, {**values, 'angle_use_custom_libvulkan': True})):
    try: e.vulkan_activation_args(o, {}, environment, old, new)
    except ValueError: pass
    else: raise AssertionError('invalid Vulkan activation accepted')
print('PASS Vulkan first activation, complete inputs and system search identity')
