#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check that the installed host context rejects cross and foreign selections."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace

owner = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('host_buildlink', owner / '../../pkgsrc/devel/electron44/files/host-buildlink.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
prefix = Path('/selected')
base = ['no', '', '', 'clang', '/selected', '/selected/pkgdb']
def check(values):
    process = SimpleNamespace(capture=lambda *args, **kwargs: SimpleNamespace(stdout=('\n'.join(values) + '\n').encode()))
    module.check_installed_context(process, ['bmake', 'wrapper'], {}, prefix)
check(base)
for index, value in ((0, 'yes'), (1, '/target'), (2, '/target'), (3, 'gcc'),
                     (4, '/foreign'), (5, '/foreign/pkgdb')):
    dirty = base.copy()
    dirty[index] = value
    try:
        check(dirty)
    except ValueError:
        continue
    raise AssertionError('accepted foreign host context: ' + str(index))
print('PASS: installed host context rejects target and foreign selections')
