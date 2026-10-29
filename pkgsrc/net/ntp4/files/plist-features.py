#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""List optional NTP programs selected by the actual target configure."""
import re
import sys
from pathlib import Path

if len(sys.argv) != 2:
    raise SystemExit('expected NTP config.status')
text = Path(sys.argv[1]).read_text()
for key, program, man in (('NTPTIME', 'ntptime', False),
                          ('TICKADJ', 'tickadj', False),
                          ('CALC_TICKADJ', 'calc_tickadj', True),
                          ('TIMETRIM', 'timetrim', False)):
    values = re.findall(r'^S\["' + key + r'_DS"\]="([^"]*)"$', text, re.M)
    if len(values) != 1 or values[0] not in ('', program):
        raise SystemExit('unexpected configure selection for ' + key)
    if values[0]:
        print('sbin/' + program)
        if man:
            suffix = re.findall(r'^S\["' + key + r'_MS"\]="([^"]*)"$', text, re.M)
            if suffix != ['8']:
                raise SystemExit('unexpected manual section for ' + key)
            print('man/man8/' + program + '.8')
