#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). No target or SSH connection is used.
"""Stored per-platform Perl cross config.sh.

Without --bmake, check every stored template and the capture/fill helper.
With --bmake, also evaluate lang/perl5 in the given cross configuration and
require that no target transport is needed unless capture is requested.
"""
import argparse
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
PERL5 = ROOT / 'pkgsrc/lang/perl5'
SPEC = importlib.util.spec_from_file_location('template', PERL5 / 'files/config-template.py')
TEMPLATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TEMPLATE)
BMAKE = None
BOARD = ('EMBERBSD_PERL_TARGET_HOST', 'EMBERBSD_PERL_TARGET_USER',
         'EMBERBSD_PERL_TARGET_DIR', 'EMBERBSD_PERL_SSH', 'EMBERBSD_PERL_SCP')
PATHS = {name: f'/build/{name.lower()}' for name in TEMPLATE.NAMES}
SET = [arg for name, value in PATHS.items() for arg in ('--set', f'{name}={value}')]


def helper(*args, check=True):
    return subprocess.run([sys.executable, '-B', str(PERL5 / 'files/config-template.py'), *args],
                          capture_output=True, text=True, check=check)


class StoredTemplates(unittest.TestCase):
    def stored(self):
        files = sorted((PERL5 / 'files/config').glob('*.sh'))
        self.assertTrue(files, 'no stored Perl config.sh')
        return files

    def test_stored_templates_are_neutral_and_identified(self):
        distname = next(line.split('=', 1)[1].strip() for line in
                        (PERL5 / 'Makefile.common').read_text().splitlines() if line.startswith('DISTNAME='))
        for path in self.stored():
            with self.subTest(path=path.name):
                helper('check', str(path))
                lines = path.read_text().splitlines()
                self.assertTrue(lines[1].startswith(f'# pkgsrc recipe: {distname} PKG_OPTIONS='), lines[1])

    def test_fill_leaves_no_placeholder_or_target_address(self):
        for path in self.stored():
            with self.subTest(path=path.name), tempfile.TemporaryDirectory() as directory:
                out = Path(directory) / 'config.sh'
                helper('fill', *SET, str(path), str(out))
                text = out.read_text()
                self.assertNotIn('@', text.replace('root@localhost', ''))
                self.assertIn(f"run='{PATHS['WRKSRC']}/Cross/no-target'", text)
                self.assertIn("targethost=''", text)


class Helper(unittest.TestCase):
    SOURCE = """#!/bin/sh
# Configuration time: Thu Oct 29 08:00:00 MSK 2026
cf_by='alice'
cf_time='Thu Oct 29 08:00:00 MSK 2026'
myhostname='buildhost'
config_args='-Dtargethost=board.local -Dtargetdir=/tmp/x.1 -Dsysroot=/build/sysroot'
run='/build/wrksrc/Cross/run'
targethost='board.local'
sysroot='/build/sysroot'
cc='/build/tooldir/bin/cc'
"""

    def test_capture_neutralises_and_roundtrips(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            (work / 'in.sh').write_text(self.SOURCE)
            helper('capture', '--identity', 'perl-0 PKG_OPTIONS=x', *SET,
                   str(work / 'in.sh'), str(work / 't.sh'))
            text = (work / 't.sh').read_text()
            for leak in ('alice', 'buildhost', 'board.local', '/tmp/x.1', '/build/', '2026'):
                self.assertNotIn(leak, text)
            self.assertIn("sysroot='@SYSROOT@'", text)
            helper('check', str(work / 't.sh'))
            helper('fill', *SET, str(work / 't.sh'), str(work / 'out.sh'))
            self.assertIn("cc='/build/tooldir/bin/cc'", (work / 'out.sh').read_text())

    def test_capture_refuses_unmapped_host_path(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            (work / 'in.sh').write_text(self.SOURCE + "ld='/opt/host/ld'\n")
            result = helper('capture', '--identity', 'x', *SET,
                            str(work / 'in.sh'), str(work / 't.sh'), check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((work / 't.sh').exists())

    def test_fill_refuses_unknown_placeholder(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            (work / 't.sh').write_text("x='@UNKNOWN@'\n")
            result = helper('fill', *SET, str(work / 't.sh'), str(work / 'o.sh'), check=False)
            self.assertNotEqual(result.returncode, 0)


class Recipe(unittest.TestCase):
    def setUp(self):
        if not BMAKE:
            self.skipTest('pass --bmake for recipe checks')

    def fail_reason(self, *assignments):
        env = {key: value for key, value in os.environ.items() if key not in BOARD}
        result = subprocess.run([BMAKE, '-C', str(PACKAGE), 'show-var', 'VARNAME=PKG_FAIL_REASON',
                                 *(f'{name}=' for name in BOARD), *assignments],
                                capture_output=True, text=True, env=env, check=True)
        return result.stdout

    def test_cross_build_needs_no_target(self):
        self.assertEqual(self.fail_reason().strip(), '')

    def test_missing_platform_file_is_explicit(self):
        self.assertIn('No stored Perl config.sh for', self.fail_reason('EMBERBSD_PERL_STORED_CONFIG=/nonexistent.sh'))

    def test_identity_mismatch_is_explicit(self):
        with tempfile.NamedTemporaryFile('w', suffix='.sh') as stored:
            stored.write('#!/bin/sh\n# pkgsrc recipe: perl-0.0 PKG_OPTIONS=none\n')
            stored.flush()
            self.assertIn('records perl-0.0', self.fail_reason(f'EMBERBSD_PERL_STORED_CONFIG={stored.name}'))

    def test_capture_still_requires_target(self):
        self.assertIn('EMBERBSD_PERL_TARGET_HOST', self.fail_reason('EMBERBSD_PERL_CAPTURE_CONFIG=yes'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--bmake', help='bmake wrapper whose MAKECONF selects a cross build')
    parser.add_argument('--package', type=Path, default=PERL5, help='lang/perl5 directory to evaluate')
    options, remaining = parser.parse_known_args()
    BMAKE, PACKAGE = options.bmake, options.package
    unittest.main(argv=[sys.argv[0], *remaining])
