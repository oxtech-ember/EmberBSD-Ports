#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check runtime stage and foundation selection without assuming a receipt."""
import argparse
import importlib.util
from pathlib import Path
import tempfile

owner = Path(__file__).resolve().parents[1] / 'electron44/files/build-electron.py'
spec = importlib.util.spec_from_file_location('electron_build', owner)
build = importlib.util.module_from_spec(spec); spec.loader.exec_module(build)
class Runtime:
    FULL_COMPONENTS = ('full',)
    def validate_stage(self, stage, *, target, required_components, base):
        assert required_components == self.FULL_COMPONENTS
        return ('stage', stage, target, base)
class Application:
    def load_clang_runtime(self, root, *, target):
        return ('installed', root, target)
sdk = {'llvm_runtime': Runtime(), 'application_toolchain': Application()}
with tempfile.TemporaryDirectory() as d:
    root = Path(d); sysroot = root / 'sysroot'; foundation = root / 'foundation'; stage = root / 'stage'
    for p in (sysroot, foundation, stage): p.mkdir()
    args = argparse.Namespace(target='amd64', sysroot=sysroot, target_runtime_stage=stage, target_runtime_base=foundation)
    selected, base, value = build.select_target_runtime(args, sdk)
    assert selected == stage and base == foundation.resolve() and value[-1] == str(foundation.resolve())
    args.target_runtime_base = None
    assert build.select_target_runtime(args, sdk)[2][-1] == str(sysroot.resolve())
    args.target_runtime_stage = None
    assert build.select_target_runtime(args, sdk)[2] == ('installed', str(sysroot), 'amd64')
    args.target_runtime_base = foundation
    try: build.select_target_runtime(args, sdk)
    except ValueError: pass
    else: raise AssertionError('accepted foundation without runtime stage')
print('target runtime foundation selection PASS')
