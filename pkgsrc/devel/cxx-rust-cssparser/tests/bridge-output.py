#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check selection of the actual Cargo bridge when stale output is present."""
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib

p = argparse.ArgumentParser(description=__doc__)
for name in ('cargo', 'cargo-helper', 'config', 'source', 'work'):
    p.add_argument('--' + name, type=Path, required=True)
p.add_argument('--jobs', type=int, default=2)
a = p.parse_args()
work = a.work.resolve(strict=True)
config = tomllib.loads(a.config.read_text())
output = Path(config['build']['target-dir']).resolve(strict=True)
if not output.is_relative_to(work):
    p.error('Cargo output must be inside the supplied isolated work directory')
build = output / config['build']['target'] / 'release/build'
if not build.is_dir():
    p.error('build the selected CSS producer before this incremental test')
helper = Path(__file__).resolve().parents[1] / 'files/build-bridge.py'
with tempfile.TemporaryDirectory(prefix='stale-css-', dir=build) as stale, \
        tempfile.TemporaryDirectory(prefix='css-bridge-test-', dir=work) as out:
    old = Path(stale) / 'out/cxxbridge/sources/cxx-rust-cssparser-impl/src'
    old.mkdir(parents=True)
    (old / 'ffi.rs.cc').write_text('#error stale bridge must not be compiled\n')
    cmd = [sys.executable, '-B', '-I', '-S', str(helper), '--cargo', str(a.cargo),
           '--cargo-helper', str(a.cargo_helper), '--config', str(a.config),
           '--source', str(a.source), '--work', out, '--bridge', str(Path(out)/'bridge.a'),
           '--include', str(Path(out)/'include'), '--jobs', str(a.jobs)]
    subprocess.run(cmd, check=True)
    if not (Path(out)/'bridge.a').is_file():
        raise ValueError('selected Cargo bridge archive is missing')
print('PASS: current Cargo bridge selected with a stale build directory present')
