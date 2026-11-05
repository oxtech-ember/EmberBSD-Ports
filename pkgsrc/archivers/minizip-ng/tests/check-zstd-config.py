#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check a real pkgsrc CMake configure against its selected zstd prefix."""
import argparse
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--build', type=Path, required=True)
p.add_argument('--prefix', type=Path, required=True)
a = p.parse_args()
cache = {}
for line in (a.build / 'CMakeCache.txt').read_text().splitlines():
    if '=' in line and ':' in line and not line.startswith(('#', '//')):
        key, value = line.split('=', 1)
        cache[key.split(':', 1)[0]] = value
assert cache.get('MZ_ZSTD') == 'ON', 'zstd compression was disabled'
assert cache.get('ZSTD_FOUND') == '1', 'selected pkg-config provider was not found'
lib = Path(cache['pkgcfg_lib_ZSTD_zstd']).resolve(strict=True)
assert lib.is_relative_to(a.prefix.resolve(strict=True)), f'outside selected prefix: {lib}'
print('PASS: selected zstd provider', lib)
