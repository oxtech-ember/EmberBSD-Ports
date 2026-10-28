#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check a completed TDB package build's Waf search paths and iconv probe."""
import argparse
from pathlib import Path
import re

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--work', required=True, type=Path, help='pkgsrc tdb work directory')
a = p.parse_args()
log = (a.work / '.work.log').read_text(errors='replace')
commands = [line for line in log.splitlines() if line.startswith('[*] cc ')]
if not commands:
    raise SystemExit('no Waf compiler commands found')
if any(re.search(r'(?:-L|-I)/usr/local/(?:lib|include)(?:\s|$)', line) for line in commands):
    raise SystemExit('Waf used the unselected /usr/local search path')
matches = list(a.work.glob('tdb-*/bin/c4che/default_cache.py'))
if len(matches) != 1:
    raise SystemExit('expected one TDB Waf configuration')
cache = matches[0].read_text(errors='replace')
if not re.search(r'^HAVE_ICONV_H\s*=\s*1\s*$', cache, re.M):
    raise SystemExit('selected iconv header was not detected')
print('TDB selected iconv routing: PASS')
