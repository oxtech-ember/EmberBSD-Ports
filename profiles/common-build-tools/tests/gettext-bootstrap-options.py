#!/usr/bin/env python3
"""Check the real pkgsrc dependency graph for both gettext compositions."""
import argparse
import os
import subprocess
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--pkgsrc', type=Path, required=True)
p.add_argument('--bmake', type=Path, required=True)
p.add_argument('--makeconf', type=Path, required=True)
p.add_argument('--make-arg', action='append', default=[])
a = p.parse_args()

def query(options):
    command = [str(a.bmake), '-C', str(a.pkgsrc / 'devel/gettext-tools'),
               *a.make_arg] + options
    command += ['-V', '${PKG_OPTIONS}', '-V', '${BUILDLINK_TREE}',
                '-V', '${CONFIGURE_ENV}', '-V', '${PLIST.style}',
                '-V', '${PKGNAME}', '-V', '${DEPENDS}', '-V', '${OPSYS}',
                '-V', '${USE_CROSS_COMPILE:Uno:tl}']
    env = dict(os.environ, MAKECONF=str(a.makeconf))
    return subprocess.check_output(command, env=env, text=True).splitlines()

full = query([])
plain = query(['PKG_OPTIONS.gettext-tools=-style'])
assert 'style' in full[0].split() and 'style' not in plain[0].split()
assert 'libcroco' in full[1].split() and 'glib2' in full[1].split()
assert 'libcroco' not in plain[1].split() and 'glib2' not in plain[1].split()
assert 'libxml2' in full[1].split() and 'libxml2' in plain[1].split()
assert 'EMBER_GETTEXT_EXTERNAL_TEXTSTYLE=yes' in full[2]
assert 'EMBER_GETTEXT_PLAIN_STYLE=yes' in plain[2]
assert full[3] == 'yes' and plain[3] == ''
assert full[4] == plain[4], (full[4], plain[4])
if full[6:8] == ['Darwin', 'no']:
    assert full[4] == 'gettext-tools-1.0nb7', full[4]
    for name in ('glib2>=', 'libcroco>='):
        assert name in full[5], (name, full[5])
    assert 'glib2>=' not in plain[5] and 'libcroco>=' not in plain[5], plain[5]
print('PASS: gettext full and bootstrap dependency graphs')
