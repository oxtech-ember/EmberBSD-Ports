#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise the production GLib test option with bmake, without a build."""
import argparse
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--bmake', type=Path, required=True)
p.add_argument('--work-parent', type=Path, required=True)
a = p.parse_args()
if not a.bmake.is_absolute() or not a.bmake.is_file() or not a.work_parent.is_dir():
    raise SystemExit('Select an absolute bmake and existing work parent')
source = (Path(__file__).resolve().parents[3] / 'pkgsrc/devel/glib2/options.mk').read_text()
source = '\n'.join('' if line.lstrip().startswith('.include ') else line
                   for line in source.splitlines())
with tempfile.TemporaryDirectory(prefix='glib-tests-option-', dir=a.work_parent) as work:
    fixture = Path(work) / 'fixture.mk'
    for opsys, opts, flag, valid in (('Linux', '', '-Dtests=false', True),
                                     ('Linux', 'tests', '-Dtests=true', True),
                                     ('Darwin', 'cocoa', '-Dtests=false', True),
                                     ('Darwin', 'cocoa tests', '-Dtests=false', False)):
        fixture.write_text(f'OPSYS={opsys}\nPKG_OPTIONS={opts}\n' + source +
                           '\nshow:\n\t@printf "%s\\n" ${PKG_FAIL_REASON:Q}\n'
                           '\t@printf "%s\\n" ${MESON_ARGS:Q}\n')
        result = subprocess.run([str(a.bmake), '-r', '-m', '/', '-f', str(fixture), 'show'],
                                capture_output=True, text=True)
        values = result.stdout.splitlines()
        if result.returncode or len(values) != 2 or bool(values[0]) == valid or flag not in values[1].split():
            raise SystemExit('Unexpected GLib test mode: ' + opsys + '/' + opts + '\n' + result.stderr)
print('PASS: four GLib test selections; no build')
