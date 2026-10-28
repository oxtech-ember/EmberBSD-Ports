#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Apply the real GN recipe and compile its bridge with the selected CXX provider."""
import argparse
import shlex
from pathlib import Path
import subprocess
import tarfile
import tempfile
import tomllib

p = argparse.ArgumentParser(description=__doc__)
for name in ('archive', 'patch', 'cxxbridge', 'include', 'cxx'):
    p.add_argument('--' + name, type=Path, required=True)
p.add_argument('--host-prefix', type=Path, help='reject host prefix headers except compiler resource headers')
a = p.parse_args()
recipe = Path(__file__).resolve().parents[3] / 'pkgsrc/devel/gn'
for name in ('archive', 'patch', 'cxxbridge', 'include', 'cxx'):
    if not getattr(a, name).is_absolute():
        p.error(name + ' must be an absolute path')
paths = {x.relative_to(a.include).as_posix() for x in a.include.rglob('*')}
if paths != {'rust', 'rust/cxx.h'} or (a.include / 'rust/cxx.h').is_symlink():
    raise ValueError('CXX include tree must contain only the derived header')
with tempfile.TemporaryDirectory(prefix='gn-cxx-check-') as tmp:
    root = Path(tmp)
    with tarfile.open(a.archive, 'r:') as archive:
        archive.extractall(root, filter='data')
    for patch in sorted((recipe / 'patches').glob('patch-*')):
        subprocess.run([str(a.patch), '--batch', '--forward', '--fuzz=0', '-p0', '-i', str(patch)],
                       cwd=root, check=True, stdout=subprocess.DEVNULL)
    bridge = root / 'src/gn/starlark/crates/ffi/src/bridge.rs'
    header = subprocess.check_output([str(a.cxxbridge), '--header'])
    if header != (a.include / 'rust/cxx.h').read_bytes():
        raise ValueError('CXX generator and selected header differ')
    for path, args in ((root/'src/gn/ffi/bridge.h', ['--header']),
                       (root/'src/gn/ffi/bridge.cc', [])):
        path.write_bytes(subprocess.check_output([str(a.cxxbridge), str(bridge), *args]))
    lock = tomllib.loads((root/'src/gn/starlark/Cargo.lock').read_text())
    for name in ('cxx', 'cxx-build', 'cxxbridge-cmd', 'cxxbridge-flags', 'cxxbridge-macro'):
        packages = [x for x in lock['package'] if x['name'] == name]
        if len(packages) != 1 or packages[0]['version'] != '1.0.205' or not packages[0].get('source', '').startswith('registry+'):
            raise ValueError('Rust bridge dependency mismatch: ' + name)
    if 'matts1/cxx' in (root/'src/gn/starlark/Cargo.toml').read_text():
        raise ValueError('private CXX fork remains active')
    for name in ('bridge', 'scope', 'value', 'session', 'intern_string'):
        depfile = root / (name + '.d')
        subprocess.run([str(a.cxx), '-std=c++23', '-Wall', '-Wextra', '-Werror',
                        '-Wno-unused-parameter', '-Wno-return-type-c-linkage',
                        '-fno-exceptions', '-fno-rtti', '-I'+str(root/'src'),
                        '-I'+str(a.include), '-MD', '-MF', str(depfile),
                        '-fsyntax-only', str(root/'src/gn/ffi'/f'{name}.cc')], check=True)
        if a.host_prefix:
            host = a.host_prefix.resolve(strict=True)
            dependencies = shlex.split(depfile.read_text().replace('\\\n', ' '))[1:]
            for item in dependencies:
                path = Path(item)
                if not path.is_absolute():
                    continue
                path = path.resolve(strict=True)
                if path.is_relative_to(host):
                    if not path.is_relative_to((host / 'lib/clang').resolve(strict=True)):
                        raise ValueError('target compilation used a native prefix header: ' + item)
print('PASS: clean GN patch series, matching CXX producer, Rust identity and five FFI units')
