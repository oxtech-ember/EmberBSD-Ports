#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""A SITES.<distfile> name is expanded when the line is parsed.

EXTRACT_SUFX gets its default later, from bsd.prefs.mk, so a recipe that uses
it in a SITES.* name without assigning it first defines SITES.<name> without
the suffix. fetch then ignores the per-file site and appends the distfile
name to MASTER_SITES instead (math/flann-lib got a codeload 404).
"""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3] / 'pkgsrc'
SITES = re.compile(r'^SITES\.[^=?+:!]*\$\{EXTRACT_SUFX\}')
ASSIGN = re.compile(r'^EXTRACT_SUFX\s*[?:!+]?=')

bad = []
for makefile in sorted(ROOT.glob('*/*/Makefile*')) + sorted(ROOT.glob('*/*/*.mk')):
    assigned = False
    for number, line in enumerate(makefile.read_text(errors='replace').splitlines(), 1):
        if ASSIGN.match(line):
            assigned = True
        elif SITES.match(line) and not assigned:
            bad.append(f'{makefile.relative_to(ROOT)}:{number}: {line.strip()}')
if bad:
    print('SITES.* name uses EXTRACT_SUFX before the recipe assigns it:', *bad, sep='\n', file=sys.stderr)
    sys.exit(1)
print('PASS: SITES.* names do not depend on the late EXTRACT_SUFX default')
