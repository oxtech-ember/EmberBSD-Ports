#!/usr/bin/env python3
"""Build target-only regressions from the existing provider Cargo graph."""
import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess

p = argparse.ArgumentParser()
p.add_argument('--work', required=True, type=Path)
p.add_argument('--cargo-output', required=True, type=Path)
p.add_argument('--target', required=True)
p.add_argument('--artifacts', required=True, type=Path)
p.add_argument('--rustc', required=True)
p.add_argument('--cxx', required=True)
p.add_argument('--stage-prefix', required=True, type=Path)
a = p.parse_args()
tests = Path(__file__).resolve().parent
out = a.work / 'regressions'
out.mkdir(parents=True, exist_ok=True)
target_deps = a.cargo_output / a.target / 'release/deps'
host_deps = a.cargo_output / 'release/deps'
artifacts = {}
for line in a.artifacts.read_text().splitlines():
    item = json.loads(line)
    if item.get('reason') != 'compiler-artifact':
        continue
    crate = item['target']['name'].replace('-', '_')
    for filename in item['filenames']:
        path = Path(filename)
        if path.parent == target_deps and path.suffix == '.rlib':
            artifacts.setdefault(crate, set()).add(path)
linker = a.work / '.cargo/cargo-tools/target-linker'
base = [a.rustc, '--edition=2021', '--target', a.target, '-C', 'linker=' + str(linker),
        '-L', 'dependency=' + str(host_deps), '-L', 'dependency=' + str(target_deps)]
for name, crates in [('ton-wallet-tolk-vectors', ['ton']),
                     ('ton-wallet-regression', ['ton', 'ed25519_dalek']),
                     ('crypto-vectors', ['crypto_secretbox', 'crypto_box'])]:
    command = base[:]
    for crate in crates:
        candidates = sorted(artifacts.get(crate, ()))
        if len(candidates) != 1:
            raise SystemExit(f'expected one {crate} rlib, found {len(candidates)}')
        command += ['--extern', crate + '=' + str(candidates[0])]
    command += [str(tests / (name + '.rs')), '-o', str(out / name)]
    subprocess.run(command, check=True)
headers = a.stage_prefix / 'include/wallet_engine'
for name in ['wallet_engine.cpp', 'wallet_engine.hpp', 'wallet_engine_scaffolding.hpp']:
    shutil.copy2(headers / name, out / name)
shutil.copy2(tests / 'wallet-ffi-consumer.cpp', out / 'wallet-ffi-consumer.cpp')
native_libs = shlex.split((a.work / 'native-static-libs').read_text())
command = shlex.split(a.cxx) + ['-std=c++20', 'wallet-ffi-consumer.cpp', 'wallet_engine.cpp',
    str(a.stage_prefix / 'lib/libtdesktop_rust.a')] + native_libs + ['-o', 'wallet-ffi-consumer']
subprocess.run(command, cwd=out, check=True)
print('Built target regressions in', out, flush=True)
