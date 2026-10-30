#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Check the sort path recorded in updatedb with real pkgsrc metadata."""
import argparse
import os
from pathlib import Path
import shlex
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
for name in ('bmake', 'pkgsrc', 'native-config', 'cross-config'):
    parser.add_argument('--' + name, required=True)
args = parser.parse_args()
package = str(Path(args.pkgsrc) / 'sysutils/findutils')

def query(config, *extra):
    env = dict(os.environ, MAKECONF=config)
    result = subprocess.run([args.bmake, '-C', package, *extra, '-V', '${CONFIGURE_ENV}'],
                            env=env, check=True, text=True, capture_output=True)
    return [word.split('=', 1)[1] for word in shlex.split(result.stdout)
            if word.startswith('ac_cv_path_SORT=')]

native = query(args.native_config, 'USE_CROSS_COMPILE=no')
assert native == [], native
cross = query(args.cross_config)
assert cross == ['/usr/bin/sort'], cross
print('updatedb native and NetBSD cross sort path: PASS')
