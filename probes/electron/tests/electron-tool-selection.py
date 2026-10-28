#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Check target Rust input and the actual selected Darwin dsymutil binding."""
import argparse
import importlib.util
from pathlib import Path
import sys
import tempfile

p=argparse.ArgumentParser()
p.add_argument('--host-prefix',type=Path,required=True)
p.add_argument('--sdk-source',type=Path,required=True)
a=p.parse_args()
path=Path(__file__).resolve().parents[1]/'electron44/files/build-electron.py'
spec=importlib.util.spec_from_file_location('electron_build',path)
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
assert Path(sys.executable).resolve() == (a.host_prefix/'bin/python3.15').resolve()
sdk=b.load_sdk(a.sdk_source)
if sys.platform=='darwin':
    native=sdk['host_prefix'].load_host_prefix(a.host_prefix,required_roles=('dsymutil',))
    selected=Path(native.tool('dsymutil')).resolve(strict=True)
with tempfile.TemporaryDirectory(prefix='electron-tools-test-') as temp:
    root=Path(temp); prefix=root/'prefix'; prefix.mkdir()
    for target,triplet in (('amd64','x86_64-unknown-netbsd'),('aarch64','aarch64-unknown-netbsd')):
        try: b.require_rust_std(prefix,target);raise AssertionError('missing std accepted')
        except ValueError as e: assert 'target Rust std missing' in str(e)
        libs=prefix/'lib/rustlib'/triplet/'lib';libs.mkdir(parents=True)
        (libs/'libstd-fixture.rlib').write_text('std')
        try: b.require_rust_std(prefix,target);raise AssertionError('missing core accepted')
        except ValueError: pass
        (libs/'libcore-fixture.rlib').write_text('core');b.require_rust_std(prefix,target)
    if sys.platform=='darwin':
        work=root/'workspace'; work.mkdir()
        b.ensure_host_dsymutil(work,native)
        dest=work/'src/tools/clang/dsymutil/bin/dsymutil'
        assert dest.is_symlink() and dest.resolve()==selected
        b.ensure_host_dsymutil(work,native)
        dest.unlink();dest.symlink_to('/usr/bin/false')
        try: b.ensure_host_dsymutil(work,native);raise AssertionError('external tool accepted')
        except ValueError as e: assert 'differs' in str(e)
        assert dest.is_symlink() and str(dest.readlink())=='/usr/bin/false'
    print('Rust input refusal and native dsymutil selection passed')
