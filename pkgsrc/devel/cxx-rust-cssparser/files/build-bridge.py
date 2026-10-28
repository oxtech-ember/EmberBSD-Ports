#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Build the CSS Rust library and CXX bridge using the common Cargo config."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tomllib

p = argparse.ArgumentParser(description=__doc__)
for name in ('cargo', 'cargo-helper', 'config', 'source', 'work', 'bridge', 'include'):
    p.add_argument('--' + name, type=Path, required=True)
p.add_argument('--jobs', type=int, required=True)
a = p.parse_args()
if a.jobs < 1:
    p.error('jobs must be positive')
for name, path in vars(a).items():
    if isinstance(path, Path) and not path.is_absolute():
        p.error(name + ' must be an absolute path')
config = tomllib.loads(a.config.read_text())
target = config['build']['target']
output = Path(config['build']['target-dir'])
cxx = Path(config['env']['TARGET_CXX']['value'])
ar = Path(config['env']['TARGET_AR']['value'])
if not all(path.is_absolute() for path in (output, cxx, ar)):
    raise ValueError('common Cargo configuration has nonabsolute tool paths')
cargo = [sys.executable, '-B', '-I', '-S', str(a.cargo_helper), 'run',
         '--cargo', str(a.cargo), '--config', str(a.config), '--source', str(a.source), '--']
metadata = json.loads(subprocess.check_output(cargo + ['metadata', '--locked', '--offline',
                                                       '--no-deps', '--format-version', '1']))
packages = [entry for entry in metadata['packages']
            if entry['name'] == 'cxx-rust-cssparser-impl'
            and Path(entry['manifest_path']).resolve() == (a.source / 'Cargo.toml').resolve()]
if len(packages) != 1:
    raise ValueError('expected one CSS parser package in Cargo metadata')
package_id = packages[0]['id']
result = subprocess.run(cargo + ['build', '--release', '--locked', '--offline',
                                 '--jobs', str(a.jobs), '--message-format=json-render-diagnostics'],
                        stdout=subprocess.PIPE, text=True)
outputs = []
for line in result.stdout.splitlines():
    event = json.loads(line)
    if event.get('reason') == 'compiler-message':
        rendered = event.get('message', {}).get('rendered')
        if rendered:
            sys.stderr.write(rendered)
    if event.get('reason') == 'build-script-executed' and event.get('package_id') == package_id:
        outputs.append(Path(event['out_dir']).resolve(strict=True))
if result.returncode:
    raise subprocess.CalledProcessError(result.returncode, result.args)
if len(outputs) != 1 or not outputs[0].is_relative_to(output.resolve(strict=True)):
    raise ValueError('expected one current Cargo build-script output for CSS parser')
build = output / target / 'release'
bridge_source = outputs[0] / 'cxxbridge/sources/cxx-rust-cssparser-impl/src/ffi.rs.cc'
include = outputs[0] / 'cxxbridge/include'
if not bridge_source.is_file():
    raise ValueError('current Cargo build did not generate the CSS CXX bridge')
if not (include / 'rust/cxx.h').is_file():
    raise ValueError('generated CXX include tree is incomplete')
if a.include.exists():
    shutil.rmtree(a.include)
shutil.copytree(include, a.include)
obj = a.work / 'cssparser-bridge.o'
subprocess.run([str(cxx), '-std=c++20', '-fPIC', '-O2', '-I' + str(a.include),
                '-c', str(bridge_source), '-o', str(obj)], check=True)
a.bridge.unlink(missing_ok=True)
subprocess.run([str(ar), 'qc', str(a.bridge), str(obj)], check=True)
static = build / 'libcxx_rust_cssparser_impl.a'
if not static.is_file():
    raise ValueError('Cargo did not produce the CSS parser static library')
shutil.copyfile(static, a.work / 'libcxx-rust-cssparser-impl.a')
