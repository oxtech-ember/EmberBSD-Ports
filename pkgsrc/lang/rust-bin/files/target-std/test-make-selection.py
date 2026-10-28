#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Check Rust std package target and explicit compiler selection with bmake."""
import argparse
import os
from pathlib import Path
import subprocess

p = argparse.ArgumentParser()
for name in ('ports', 'pkgsrc', 'make', 'makeconf', 'make-module-dir', 'host-prefix'):
    p.add_argument('--'+name, type=Path, required=True)
a = p.parse_args()
env = dict(os.environ, PATH=str(a.host_prefix/'bin')+':'+str(a.host_prefix/'sbin'), MAKECONF=str(a.makeconf))
common = ['EMBERBSD_DARWIN_BOOTSTRAP=yes', 'EMBERBSD_SDK_SOURCE=/sdk',
          'EMBERBSD_RUST_COMPILER_PREFIX=/compiler', 'EMBERBSD_RUST_TARGET_SYSROOT=/sysroot',
          'EMBERBSD_RUST_MACOS_SDK=/macsdk', 'EMBERBSD_RUST_MACOS_MINIMUM=26.0',
          'EMBERBSD_RUST_LOCK_ROOT=/locks', 'EMBERBSD_RUST_LINK_CONTEXT=/context']
def query(package, options=()):
    recipe = a.ports/'pkgsrc/lang'/package/'Makefile'
    cwd = a.pkgsrc/'lang'/package
    argv = [str(a.make),'-m',str(a.make_module_dir),'-f',str(recipe),*common,*options,
            '-V','${RUST_STD_TARGET}','-V','${RUST_TARGET_TRIPLE}','-V','${PKG_FAIL_REASON}']
    r = subprocess.run(argv,cwd=cwd,env=env,text=True,capture_output=True,check=True)
    return r.stdout.splitlines()
for package, target, triple in (('rust-std-x86_64-netbsd','amd64','x86_64-unknown-netbsd'),
                                ('rust-std-aarch64-netbsd','aarch64','aarch64-unknown-netbsd')):
    rows = query(package)
    assert rows[:2] == [target,triple] and not rows[2], rows
rows = query('rust-std-x86_64-netbsd',['EMBERBSD_RUST_TARGET_COMPILER_FAMILY=gcc'])
assert 'supports Clang only' in rows[2], rows
rows = query('rust-std-aarch64-netbsd',['EMBERBSD_RUST_TARGET_COMPILER_FAMILY=gcc'])
assert 'requires EMBERBSD_RUST_GCC_REASON' in rows[2], rows
print('both LLVM targets and explicit GCC refusal: PASS')
