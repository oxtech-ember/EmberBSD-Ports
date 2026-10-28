#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check that the CSS owner source plan matches its patched Cargo.lock."""
import argparse
from pathlib import Path
import subprocess
import tarfile
import tempfile
import tomllib
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--archive', type=Path, required=True)
p.add_argument('--patch-tool', type=Path, required=True)
a = p.parse_args()
root = Path(__file__).resolve().parents[4]
toolkit = root / 'probes/plasma-mobile/toolkit'
recipe = root / 'pkgsrc/devel/cxx-rust-cssparser'
with tempfile.TemporaryDirectory(prefix='cssparser-lock-') as tmp:
    work = Path(tmp)
    with tarfile.open(a.archive, 'r:gz') as tar:
        src = tar.extractfile('cxx-rust-cssparser-1.1.0/rust/Cargo.lock')
        if src is None:
            raise ValueError('upstream lock not found')
        (work / 'rust').mkdir()
        (work / 'rust/Cargo.lock').write_bytes(src.read())
    subprocess.run([str(a.patch_tool), '--batch', '--fuzz=0', '-p0', '-i',
                    str(recipe / 'patches/patch-rust_Cargo.lock')], cwd=work,
                   check=True, stdout=subprocess.DEVNULL)
    packages = tomllib.loads((work / 'rust/Cargo.lock').read_text())['package']
expected = {}
for package in packages:
    if not package.get('source', '').startswith('registry+'):
        continue
    name, version = package['name'], package['version']
    archive = f'{name}-{version}.crate'
    expected[archive] = (package['checksum'], f'https://static.crates.io/crates/{name}/{archive}')
rows = [line.split('\t') for line in (toolkit / 'sources.tsv').read_text().splitlines()
        if line.startswith('devel/cxx-rust-cssparser\t')]
actual = {row[1]: (row[2], row[3]) for row in rows if row[1].endswith('.crate')}
if len(actual) != len(rows) - 1 or actual != expected:
    raise ValueError('CSS crate source plan differs from patched Cargo.lock')
print(f'PASS: {len(expected)} CSS crate source identities match the patched lock')
