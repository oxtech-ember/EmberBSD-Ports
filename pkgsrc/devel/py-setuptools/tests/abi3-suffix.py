#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Check the stable ABI suffix that setuptools gives py_limited_api
# extensions. pkgsrc builds CPython with EXT_SUFFIX ".so"; setuptools
# 84 then returned no abi3 suffix and named archivers/py-zopfli's module
# zopfli.so instead of the zopfli.abi3.so in its PLIST.
#
# Usage: python3 abi3-suffix.py SETUPTOOLS_SOURCE_DIR

import sys

sys.path.insert(0, sys.argv[1])
from setuptools.command import build_ext  # noqa: E402

CASES = [
    # pkgsrc NetBSD target and Darwin host configurations
    ({'EXT_SUFFIX': '.so', 'SOABI': 'cpython-315', 'SOABI_PLATFORM': 0},
     '.abi3.so'),
    ({'EXT_SUFFIX': '.so', 'SOABI': 'cpython-315-darwin',
      'SOABI_PLATFORM': 'darwin'}, '.abi3-darwin.so'),
    ({'EXT_SUFFIX': '.so', 'SOABI': 'cpython-314t',
      'Py_GIL_DISABLED': 1}, None),
    # upstream configurations keep their results
    ({'EXT_SUFFIX': '.cpython-315-x86_64-linux-gnu.so',
      'SOABI': 'cpython-315-x86_64-linux-gnu',
      'SOABI_PLATFORM': 'x86_64-linux-gnu'}, '.abi3-x86_64-linux-gnu.so'),
    ({'EXT_SUFFIX': '.so', 'SOABI': 'pypy311-pp73'}, None),
]

failed = 0
for config, want in CASES:
    build_ext.get_config_var = lambda name, c=config: c.get(name)
    got = build_ext.get_abi3_suffix()
    if got != want:
        print(f'FAIL: {config}: got {got!r}, want {want!r}')
        failed = 1
if failed:
    sys.exit(1)
print('PASS: setuptools gives pkgsrc CPython the stable ABI suffix')
