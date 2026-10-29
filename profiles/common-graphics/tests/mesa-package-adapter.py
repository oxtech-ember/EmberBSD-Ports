#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Test real argument construction and adapter input rejection without compiling."""
import importlib.util
import os
from pathlib import Path
import tempfile

owner = Path(__file__).resolve().parents[1] / 'cross/prepare-mesa-package-tests.py'
spec = importlib.util.spec_from_file_location('mesa_package', owner)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp); tools = root/'tools'; (tools/'bin').mkdir(parents=True); sysroot=root/'sysroot'; sysroot.mkdir()
    for name in ('x86_64--netbsd-gcc','x86_64--netbsd-clang','x86_64--netbsd-readelf'):
        (tools/'bin'/name).symlink_to('/usr/bin/true')
    gcc = m.render_command(tools,sysroot,'x86_64',root/'probe.c',root/'out')
    assert gcc[0]=='gcc' and any(x.startswith('-B') for x in gcc[4]) and '-Wl,-rpath,/usr/pkg/gcc16/lib' in gcc[4]
    (tools/'target.mk').write_text(f'_EMBER_TARGET_FAMILY:= clang\n_EMBER_TARGET_TARGET:= amd64\n_EMBER_TARGET_SYSROOT:= {sysroot}\n')
    clang = m.render_command(tools,sysroot,'x86_64',root/'probe.c',root/'out')
    assert clang[0]=='clang' and not any(x.startswith('-B') or x.startswith('--sysroot=') for x in clang[4]) and '-Wl,-rpath,/usr/pkg/llvm/lib' in clang[4]
    (tools/'target.mk').write_text('_EMBER_TARGET_FAMILY:= clang\n_EMBER_TARGET_TARGET:= aarch64\n_EMBER_TARGET_SYSROOT:= /wrong\n')
    try: m.render_command(tools,sysroot,'x86_64',root/'probe.c',root/'out')
    except ValueError: pass
    else: raise AssertionError('mismatched adapter accepted')
print('PASS: GCC/Clang generated commands and mismatched adapter refusal')
