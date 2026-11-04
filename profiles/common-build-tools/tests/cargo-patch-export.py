#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check every common Cargo patch is present at its registry export path."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
registry = ROOT / 'profiles/common-build-tools/cargo-patches/registry.json'
records = json.loads(registry.read_text())
lines = (ROOT / 'pkgsrc/export.conf').read_text().splitlines()
def missing(lines):
    mapped = {tuple(line.split('\t')[1:]) for line in lines if line.startswith('file\t')}
    required = {(f'profiles/common-build-tools/cargo-patches/{item["patch"]}',
                 f'lang/rust/emberbsd-cargo-patches/{item["patch"]}')
                for item in records.values()}
    for source, _ in required:
        assert (ROOT / source).is_file(), source
    return required - mapped
assert not missing(lines), sorted(missing(lines))
# The omission that blocked librsvg must be detected.
without = [line for line in lines if 'derive_more-impl-2.1.1.patch' not in line]
assert len(missing(without)) == 1
print(f'PASS: {len(records)} Cargo patch registry entries exported')
