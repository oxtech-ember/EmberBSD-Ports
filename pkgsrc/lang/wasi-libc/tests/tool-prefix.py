#!/usr/bin/env python3
# Origin: EmberBSD (AI-assisted).
"""Check actual pkgsrc command expansion for native and cross install prefixes."""
import argparse
import os
from pathlib import Path
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--recipe', required=True, type=Path)
p.add_argument('--host-prefix', required=True, type=Path)
p.add_argument('--target-prefix', required=True, type=Path)
p.add_argument('--makeconf', required=True, type=Path)
a = p.parse_args()
host, target = str(a.host_prefix), str(a.target_prefix)
if not a.host_prefix.is_absolute() or not a.target_prefix.is_absolute() or host == target:
    p.error('select distinct absolute host and target prefixes')
env = dict(os.environ, PATH=host + '/bin', MAKECONF=str(a.makeconf))
base = [host + '/bin/bmake', 'EMBERBSD_DARWIN_BOOTSTRAP=yes', 'TOOLBASE=' + host]
def make(*args):
    return subprocess.run(base + list(args), cwd=a.recipe, env=env, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout
for prefix in (host, target):
    out = make('-n', 'do-configure', 'do-build', 'do-install', 'PREFIX=' + prefix)
    for tool in ('cmake', 'ninja', 'clang', 'llvm-ar', 'llvm-ranlib', 'llvm-nm', 'wasm-ld'):
        assert host + '/bin/' + tool in out, tool
        if prefix != host:
            assert prefix + '/bin/' + tool not in out, tool
    assert '-DCMAKE_INSTALL_PREFIX=' + prefix + '/wasi' in out
    assert '-DBUILTINS_LIB=' + host + '/lib/clang/' in out
    values = make('-V', '${FIND}', '-V', '${SORT}', '-V', '${SED}', 'PREFIX=' + prefix).splitlines()
    assert values == [host + '/bin/gfind', host + '/bin/gsort', host + '/bin/gsed'], values
print('PASS: native and distinct target prefixes select host tools and WASI builtins')
