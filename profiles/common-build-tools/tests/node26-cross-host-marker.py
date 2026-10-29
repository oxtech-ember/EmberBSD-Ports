#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check default cross host selection is keyed and guarded before configure."""
import argparse
import os
from pathlib import Path
import re
import subprocess

parser = argparse.ArgumentParser()
for name in ('bmake', 'makeconf', 'pkgsrc', 'make-module-dir'):
    parser.add_argument('--' + name, type=Path, required=True)
a = parser.parse_args()
paths = {name: getattr(a, name).resolve(strict=True) for name in
         ('bmake', 'makeconf', 'pkgsrc', 'make_module_dir')}
env = dict(os.environ, MAKECONF=str(paths['makeconf']))
cmd = [str(paths['bmake']), '-m', str(paths['make_module_dir']),
       '-C', str(paths['pkgsrc'] / 'lang/nodejs')]
variables = ['NODE_HOST_PROVIDER_PREFIX', 'NODE_HOST_ICU_PREFIX',
             'WRKDIR_BASENAME', '_NODE_HOST_SELECTION_MARKER', '_NODE_HOST_SELECTION_SHA']
for var in variables:
    cmd += ['-V', '${' + var + '}']
p = subprocess.run(cmd, env=env, text=True, capture_output=True, check=True)
values = p.stdout.splitlines()
assert len(values) == len(variables), values
provider, icu, work, marker, digest = values
assert provider and icu == provider, values
assert re.fullmatch(r'[0-9a-f]{64}', digest), values
assert re.search(r'-[0-9A-Fa-f]+$', work), values
assert marker.endswith('/' + work + '/.node-host-selection'), values
print('Node cross default host prefixes, keyed work and full marker: PASS')
