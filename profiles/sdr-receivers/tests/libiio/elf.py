#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
import subprocess
import sys
from pathlib import Path
prefix = Path(sys.argv[1])
readelf = sys.argv[2]
for filename, soname in [('libiio.so.0','libiio.so.0'),('libiio.so.1','libiio.so.1')]:
    text = subprocess.check_output([readelf,'-d',str(prefix/'lib'/filename)],text=True)
    if not any('SONAME' in line and '['+soname+']' in line for line in text.splitlines()):
        raise SystemExit('FAIL installed ABI library lacks expected SONAME: '+filename)
    for line in text.splitlines():
        if any(x in line for x in ('NEEDED','RPATH','RUNPATH')) and ('/Users/' in line or '/home/' in line):
            raise SystemExit('FAIL build path in dynamic metadata: '+line)
print('PASS ABI0 and ABI1 SONAME and target loader paths')
