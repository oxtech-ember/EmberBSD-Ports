#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise the real QtBase options policy with bmake; build nothing."""
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
source = (Path(__file__).resolve().parents[1] / 'options.mk').read_text()
# Stub the external pkgsrc includes; leave the real role policy intact.
source = '\n'.join('' if line.lstrip().startswith('.include ') or
                   line.lstrip().startswith('.  include ') else line
                   for line in source.splitlines())
cases = (
    ('Linux', 'no', 'software-rendering headless-generators', True),
    ('Linux', 'no', 'headless-generators', False),
    ('NetBSD', 'yes', 'software-rendering headless-generators', False),
    ('Linux', 'no', 'software-rendering headless-generators gtk3', False),
    ('Linux', 'no', 'software-rendering', True),
)
with tempfile.TemporaryDirectory(prefix='qt-headless-metadata-', dir=args.work_parent) as work:
    fixture = Path(work) / 'fixture.mk'
    for opsys, cross, options, accepted in cases:
        fixture.write_text(f'OPSYS={opsys}\nUSE_CROSS_COMPILE={cross}\nPKG_OPTIONS={options}\n'
                           + source + '\nshow:\n\t@printf "%s\\n" ${PKG_FAIL_REASON:Q}\n'
                           + '\t@printf "%s\\n" ${CMAKE_CONFIGURE_ARGS:Q}\n')
        result = subprocess.run([str(args.bmake), '-r', '-m', '/', '-f', str(fixture), 'show'],
                                capture_output=True, text=True)
        values = result.stdout.splitlines()
        if result.returncode or len(values) != 2 or bool(values[0]) == accepted:
            raise SystemExit('Unexpected Qt option result: ' + options + '\n' + result.stderr)
        for feature in ('xcb', 'xlib', 'wayland', 'qtwaylandscanner'):
            if (f'-DFEATURE_{feature}:BOOL=OFF' in values[1]) != ('headless-generators' in options):
                raise SystemExit('Unexpected ' + feature + ' feature selection: ' + options)
print('PASS: five native and cross option selections; no build')
