#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted dependency check regressions.
"""Subprocess checks for scripts/check-export-depends.py.

Set PKG_ADMIN to a native pkg_admin to use the real pattern matcher.
Otherwise a small fixture matcher handles NAME-VERSION and NAME>=VERSION.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'check-export-depends.py'

FAKE_BMAKE = r'''
import json, os, pathlib, sys
args = sys.argv[1:]
# Only the build-host facts may be reused; OPSYS can differ between packages.
if '${MAKEFLAGS}' in args:
    assert 'USE_CROSS_COMPILE=no' in args
    print(r'OPSYS=Fixture NATIVE_OPSYS=Fixture OSX_SDK_PATH=/SDK\ 1 _PATH_ORIG=/bin')
    sys.exit()
if os.environ.get('MAKEFLAGS') != r'NATIVE_OPSYS=Fixture OSX_SDK_PATH=/SDK\ 1':
    sys.exit('build-host facts were not reused alone')
directory = pathlib.Path(args[args.index('-C') + 1])
root = directory.parents[1]
settings = dict(a.split('=', 1) for a in args if '=' in a and not a.startswith('${'))
pkgdb = pathlib.Path(settings['PKG_DBDIR'])
if not pkgdb.is_dir() or any(pkgdb.iterdir()):
    sys.exit('package database is not empty')
package = directory.relative_to(root).as_posix()
values = json.loads((root / 'metadata.json').read_text())[package]
if values.get('fail'):
    sys.exit('fixture query failure')
values = dict(values.get('common', {}), **values.get(settings['USE_CROSS_COMPILE'], {}))
required = settings.get('PKGNAME_REQD')
if required and required in values.get('required', {}):
    values['PKGNAME'] = values['required'][required]
for arg in args:
    if arg.startswith('${'):
        value = values.get(arg[2:-1], '')
        print(value.format(TARGET=settings.get('TARGET_MACHINE_ARCH', '')))
'''

FAKE_PKG_ADMIN = r'''
import re, sys
_, command, pattern, name = sys.argv
assert command == 'pmatch'
def split(text):
    base, _, version = text.rpartition('-')
    return base, [int(x) for x in re.findall(r'\d+', version)]
match = re.fullmatch(r'([^<>=]+)>=(.+)', pattern)
if match:
    base, version = split(name)
    sys.exit(0 if base == match.group(1)
             and version >= [int(x) for x in re.findall(r'\d+', match.group(2))] else 1)
sys.exit(0 if pattern == name else 1)
'''

METADATA = {
    'x11/layer-shell': {'common': {'PKGNAME': 'layer-shell-6.7.4'}},
    'x11/session': {'common': {
        'PKGNAME': 'session-2.3',
        'DEPENDS': 'layer-shell>=6.8.0:../../x11/layer-shell py314-binding>=1:../../lang/py-binding',
        'BUILD_DEPENDS': 'absent>=1:../../x11/absent',
        'TOOL_DEPENDS': 'generator>=2:../../devel/generator '
                        'cross-tool-aarch64>=1:../../cross/cross-tool'},
        'yes': {'CROSSTARGETSETTINGS': 'TARGET_MACHINE_ARCH=aarch64'}},
    'cross/cross-tool': {'common': {'PKGNAME': 'cross-tool-{TARGET}-1'}},
    'devel/generator': {'common': {'DEPENDS': 'helper>=1:../../devel/helper'},
                        'yes': {'PKGNAME': 'generator-1'},
                        'no': {'PKGNAME': 'generator-2'}},
    'devel/helper': {'fail': True},
    'lang/py-binding': {'common': {'PKGNAME': 'py313-binding-1',
                                   'required': {'py314-binding>=1': 'py314-binding-1'}}},
    'devel/good': {'common': {'PKGNAME': 'good-1',
                              'DEPENDS': 'layer-shell>=6.7:../../x11/layer-shell'}},
}


class CheckTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name)
        self.pkgsrc = self.path / 'pkgsrc'
        for package in METADATA:
            (self.pkgsrc / package).mkdir(parents=True)
            (self.pkgsrc / package / 'Makefile').write_text('# Fixture\n')
        (self.pkgsrc / 'mk').mkdir()
        (self.pkgsrc / 'metadata.json').write_text(json.dumps(METADATA))
        self.makeconf = self.path / 'mk.conf'
        self.makeconf.write_text('# Fixture\n')
        self.bmake = self.tool('bmake', FAKE_BMAKE)
        self.pkg_admin = os.environ.get('PKG_ADMIN') or self.tool('pkg_admin', FAKE_PKG_ADMIN)

    def tool(self, name, body):
        path = self.path / name
        path.write_text('#!' + sys.executable + '\n' + body)
        path.chmod(0o755)
        return str(path)

    def check(self, *roots):
        work = self.path / 'work'
        command = [sys.executable, '-B', str(SCRIPT), '--pkgsrc', str(self.pkgsrc),
                   '--makeconf', str(self.makeconf), '--bmake', str(self.bmake),
                   '--pkg-admin', str(self.pkg_admin), '--work', str(work)]
        for root in roots:
            command += ['--root', root]
        completed = subprocess.run(command, text=True, capture_output=True)
        rows = (work / 'findings.tsv').read_text().splitlines()[1:]
        return completed, [tuple(row.split('\t')) for row in rows]

    def test_reports_every_gap(self):
        completed, rows = self.check('x11/session')
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertIn('FAIL: 3 dependency findings', completed.stderr)
        self.assertEqual(sorted(r[0] for r in rows), ['missing', 'query-failed', 'unsatisfied'])
        unsatisfied = [r for r in rows if r[0] == 'unsatisfied'][0]
        self.assertEqual(unsatisfied[1:5], ('target:x11/session', 'DEPENDS',
                                            'layer-shell>=6.8.0', 'target:x11/layer-shell'))
        self.assertTrue(unsatisfied[5].startswith('layer-shell-6.7.4'))
        self.assertIn(('missing', 'target:x11/session', 'BUILD_DEPENDS', 'absent>=1', '',
                       'missing provider: ../../x11/absent'), rows)
        # The host tools satisfy their patterns: the generator in the host role,
        # the cross tool with the target settings. Their dependencies are checked.
        failed = [r for r in rows if r[0] == 'query-failed'][0]
        self.assertEqual(failed[1], 'host:devel/helper')

    def test_whole_tree_is_default(self):
        completed, rows = self.check()
        self.assertEqual(completed.returncode, 1)
        consumers = {r[1] for r in rows}
        self.assertIn('target:devel/helper', consumers)
        self.assertIn('host:devel/helper', consumers)

    def test_pass(self):
        completed, rows = self.check('devel/good', 'lang/py-binding')
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(rows, [])
        self.assertIn('PASS: every dependency pattern of 3 checked packages', completed.stdout)


if __name__ == '__main__':
    unittest.main()
