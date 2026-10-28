#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check target and native Rust tool separation in the actual bmake include."""
import argparse
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

p = argparse.ArgumentParser()
p.add_argument('--bmake', type=Path, required=True)
p.add_argument('--prefix', type=Path, required=True)
a = p.parse_args()
prefix = a.prefix.resolve(strict=True)
rustc = (prefix/'bin/rustc').resolve(strict=True)
version = subprocess.run([str(rustc), '-vV'], check=True, capture_output=True, text=True).stdout
host = next(line.split(': ', 1)[1] for line in version.splitlines() if line.startswith('host: '))
host_key = host.upper().replace('-', '_')
source = Path(__file__).resolve().parents[1] / 'cross.mk'
env = os.environ.copy(); env['PATH'] = str(prefix/'bin') + os.pathsep + str(prefix/'sbin')
with tempfile.TemporaryDirectory(prefix='glycin-cross-test-') as tmp:
    makefile = Path(tmp)/'Makefile'
    makefile.write_text('.include "' + str(source) + '"\n')
    for target, triple, gnu, std in (('amd64','x86_64-unknown-netbsd','x86_64--netbsd','rust-std-x86_64-netbsd'),
                                     ('aarch64','aarch64-unknown-netbsd','aarch64--netbsd','rust-std-aarch64-netbsd')):
        args=[str(a.bmake),'-f',str(makefile),'EMBERBSD_CROSS_TARGET='+target,
              'TOOLBASE='+str(prefix),'EMBERBSD_NATIVE_AWK='+str(prefix/'bin/nawk'),'TOOLDIR=/selected/cross','PREFIX=/usr/pkg','WRKDIR='+tmp,
              'WRAPPER_BINDIR=/selected/wrappers','EMBERBSD_CROSS_BUILD_AR='+str(prefix/'bin/llvm-ar'),
              'EMBERBSD_CROSS_BUILD_CC='+str(prefix/'bin/clang'),'EMBERBSD_CROSS_BUILD_CXX='+str(prefix/'bin/clang++')]
        for var in ('MAKE_ENV','MESON_CROSS.rust_target','MESON_BINARY.nm','TOOL_DEPENDS'):
            args += ['-v',var]
        result = subprocess.run(args, env=env, check=True, capture_output=True, text=True).stdout.splitlines()
        if len(result)!=4: raise AssertionError(result)
        settings=shlex.split(result[0]); key=triple.upper().replace('-','_'); cc_key=triple.replace('-','_')
        for expected in ('HOST_AR='+str(prefix/'bin/llvm-ar'),
                         'CARGO_TARGET_'+key+'_LINKER=/selected/wrappers/cc',
                         'CARGO_TARGET_'+host_key+'_LINKER='+str(prefix/'bin/clang'),
                         'AR_'+cc_key+'=/selected/cross/bin/'+gnu+'-ar'):
            assert expected in settings, (target, expected, settings)
        assert result[1].strip("'")==triple, result[1]
        assert result[2]=='/selected/cross/bin/'+gnu+'-nm', result[2]
        assert any(x.startswith(std+'-1.99.1') for x in result[3].split()), result[3]
print('glycin amd64/aarch64 target and selected native tools: PASS')
