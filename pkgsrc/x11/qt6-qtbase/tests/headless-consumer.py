#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise QtBase's consumer buildlink graph under installed option sets."""
import argparse
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--bmake', type=Path, required=True)
parser.add_argument('--work-parent', type=Path, required=True)
args = parser.parse_args()
if not args.bmake.is_absolute() or not args.bmake.is_file():
    raise SystemExit('Select an absolute bmake executable')
if not args.work_parent.is_absolute() or not args.work_parent.is_dir():
    raise SystemExit('Select an existing absolute work parent')
source = (Path(__file__).resolve().parents[1] / 'buildlink3.mk').read_text()
# Record the actual buildlink inclusions; the installed-option lookup is an input.
lines = []
for line in source.splitlines():
    if line.lstrip().startswith('.include '):
        line = 'TEST_INCLUDES+= ' + line.split('"')[1]
    lines.append(line)
source = '\n'.join(lines)
x11 = {'../../x11/libxcb/buildlink3.mk', '../../x11/libX11/buildlink3.mk',
       '../../x11/xcb-util/buildlink3.mk', '../../x11/libxkbcommon/buildlink3.mk'}
with tempfile.TemporaryDirectory(prefix='qt-headless-consumer-', dir=args.work_parent) as work:
    fixture = Path(work) / 'fixture.mk'
    for opsys, cross, options, want_x11 in (
        ('Linux', 'no', 'software-rendering headless-generators', False),
        ('Linux', 'no', 'software-rendering', True),
        ('NetBSD', 'yes', '', True),
        ('Darwin', 'no', '', False),
    ):
        fixture.write_text(f'OPSYS={opsys}\nUSE_CROSS_COMPILE={cross}\n'
                           f'PKG_BUILD_OPTIONS.qt6-qtbase={options}\n' + source +
                           '\nshow:\n\t@printf "%s\\n" ${TEST_INCLUDES:Q}\n')
        result = subprocess.run([str(args.bmake), '-r', '-m', '/', '-f', str(fixture), 'show'],
                                capture_output=True, text=True)
        if result.returncode:
            raise SystemExit('bmake consumer failed: ' + result.stderr)
        includes = set(result.stdout.split())
        if bool(includes & x11) != want_x11 or (want_x11 and not x11 <= includes):
            raise SystemExit(f'Unexpected consumer X11 graph for {opsys}/{options}: {sorted(includes & x11)}')
        if '../../fonts/fontconfig/buildlink3.mk' not in includes and opsys != 'Darwin':
            raise SystemExit('Consumer lost generic Unix font support')
print('PASS: four installed-option consumer graphs; no build')
