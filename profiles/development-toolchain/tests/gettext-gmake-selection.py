#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check gettext selects common GNU make when the initial one is too old."""
import argparse
from pathlib import Path
import subprocess

p = argparse.ArgumentParser()
for option in ('pkgsrc', 'bmake', 'makeconf', 'shell', 'old-gmake', 'prefix'):
    p.add_argument('--' + option, type=Path, required=True)
a = p.parse_args()
old = str(a.old_gmake) + ' SHELL=' + str(a.shell) + ' MAKECONF=' + str(a.makeconf)
base = [str(a.bmake), '-m', str(a.prefix / 'share/mk'), 'SHELL=' + str(a.shell),
        'MAKECONF=' + str(a.makeconf), 'EMBERBSD_DARWIN_BOOTSTRAP=yes',
        'EMBERBSD_DARWIN_GMAKE=' + old, '-C', str(a.pkgsrc / 'devel/gettext-tools')]
variables = ('GMAKE_REQD', '_TOOLS_VERSION.gmake', '_TOOLS_USE_PKGSRC.gmake',
             'TOOLS_PATH.gmake', 'TOOL_DEPENDS')
def query(extra):
    command = base + extra
    for name in variables:
        command.extend(('-V', '${' + name + '}'))
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    lines = result.stdout.splitlines()
    if len(lines) != len(variables):
        raise AssertionError('unexpected metadata output')
    return dict(zip(variables, lines))

baseline = query(['GMAKE_REQD=3.81'])
candidate = query([])
assert baseline['_TOOLS_VERSION.gmake'] == '3.81'
assert baseline['_TOOLS_USE_PKGSRC.gmake'] == 'no'
assert baseline['TOOLS_PATH.gmake'] == str(a.old_gmake)
assert candidate['GMAKE_REQD'] == '4.0'
assert candidate['_TOOLS_USE_PKGSRC.gmake'] == 'yes'
assert candidate['TOOLS_PATH.gmake'] == str(a.prefix / 'bin/gmake')
assert 'gmake>=4.0:../../devel/gmake' in candidate['TOOL_DEPENDS']
print('gettext selects common GNU make for an incompatible initial make: PASS')
