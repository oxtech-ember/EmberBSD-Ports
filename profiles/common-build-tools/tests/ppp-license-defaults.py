#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted). Upstream status: not submitted.
"""Check build and package tool defaults for the PPP license expression."""
import argparse
import os
from pathlib import Path
import subprocess

p = argparse.ArgumentParser(description=__doc__)
for name in ('bmake', 'pkg-admin', 'package', 'makeconf', 'path', 'tmpdir'):
    p.add_argument('--' + name, required=True)
a = p.parse_args()
for x in (a.bmake, a.pkg_admin, a.package, a.makeconf, a.tmpdir):
    assert Path(x).is_absolute()
env = dict(os.environ, PATH=a.path, MAKECONF=a.makeconf, TMPDIR=a.tmpdir)
r = subprocess.run([a.bmake, '-C', a.package, '-V', '${_ACCEPTABLE_LICENSE}',
                    '-V', '${SKIP_LICENSE_CHECK}'], env=env, text=True, capture_output=True)
assert r.returncode == 0 and not r.stderr and r.stdout.splitlines() == ['yes', 'no'], (r.stdout, r.stderr)
for condition, expected in (('ppp-cmu AND ppp-attribution AND 2-clause-bsd AND modified-bsd AND gnu-gpl-v2', 'yes'),
                            ('ppp-cmu AND unknown-ppp-license', 'no')):
    r = subprocess.run([a.pkg_admin, '-C', '/dev/null', 'check-license', condition],
                       env=env, text=True, capture_output=True)
    assert r.returncode == 0 and not r.stderr and r.stdout.strip() == expected, (r.stdout, r.stderr)
print('PPP build and pkg_install license defaults: PASS')
