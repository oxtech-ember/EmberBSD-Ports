#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check selected NTP install locations using the actual upstream script."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
for name in ('source', 'host-prefix', 'shell', 'work-dir'):
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
source = a.source / 'sntp'
env = {'PATH': str(a.host_prefix / 'bin') + ':' + str(a.host_prefix / 'gnu/bin')}
with tempfile.TemporaryDirectory(dir=a.work_dir) as temp:
    result = subprocess.run([str(a.shell), str(source / 'scripts/genLocInfo'),
                             '-d', temp, '-f', 'loc/pkgsrc'],
                            cwd=source, env=env, capture_output=True, text=True, check=True)
    lines = set(result.stdout.splitlines())
    for expected in ('GENLOCINFOFILE=loc/pkgsrc', 'NTPQ_DS=ntpq',
                     'NTP_KEYGEN_DS=ntp-keygen', 'SNTP_MS=1', 'GENLOCINFO=OK'):
        assert expected in lines, (expected, result.stdout, result.stderr)
print('NTP selected package install locations: PASS')
