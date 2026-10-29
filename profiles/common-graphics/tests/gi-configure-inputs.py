#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). No target, SSH connection or download is used.
"""GI target query inputs are checked at configure time, not at parse time.

A bulk fetch evaluates every recipe before the build host is configured for
target queries. An unset or absent EMBERBSD_GI_QUERY_CONFIG must not set
PKG_FAIL_REASON, because that also refuses fetch. The configure-time check
target must still refuse it with its message, run before any target query,
and accept an existing file. The cross configuration already verifies
EMBERBSD_SDK_SOURCE, EMBERBSD_CROSS_BUILD_CC and EMBERBSD_CROSS_BUILD_PYTHON
for every package while it is parsed, so the test keeps the configured ones.

Usage: gi-configure-inputs.py --bmake BMAKE --pkgsrc TREE --makeconf CROSS_MAKECONF
"""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ARGS = None
# Recipe and its input check target.
RECIPES = (
    ('devel/gobject-introspection', 'emberbsd-gi-inputs'),
    ('devel/glib2-introspection', 'emberbsd-gi-inputs'),
    ('devel/pango', 'emberbsd-gi-inputs'),
    ('graphics/gdk-pixbuf2', 'emberbsd-gi-inputs'),
    ('devel/talloc', 'emberbsd-talloc-inputs'),
    ('databases/tdb', 'emberbsd-tdb-inputs'),
)
MESSAGE = 'EMBERBSD_GI_QUERY_CONFIG must name an existing absolute file without shell metacharacters'
ABSENT = ((), ('EMBERBSD_GI_QUERY_CONFIG=/ember-missing-gi-query.json',),
          ('EMBERBSD_GI_QUERY_CONFIG=relative.json',))


def bmake(recipe, *args):
    return subprocess.run([ARGS.bmake, '-C', str(ARGS.pkgsrc / recipe), f'MAKECONF={ARGS.makeconf}', *args],
                          capture_output=True, text=True, timeout=300, env=dict(os.environ, LC_ALL='C'))


class ConfigureTimeInputs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        query = Path(cls.temp.name) / 'query.json'
        query.write_text('{}\n')
        cls.valid = ('EMBERBSD_GI_QUERY_CONFIG=' + str(query),)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_real_cross_configuration(self):
        for recipe, _target in RECIPES:
            with self.subTest(recipe=recipe):
                result = bmake(recipe, '-V', '${USE_CROSS_COMPILE}', '-V', '${EMBERBSD_GI_QUERY_CONFIG:Uunset}')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.split(), ['yes', 'unset'],
                                 'a real cross MAKECONF without a GI query configuration is required')

    def test_absent_query_config_does_not_refuse_fetch(self):
        for recipe, _target in RECIPES:
            for absent in ABSENT:
                with self.subTest(recipe=recipe, absent=absent):
                    result = bmake(recipe, *absent, '-V', '${PKG_FAIL_REASON}')
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertNotIn('must name', result.stdout)
                    self.assertNotIn('GdkPixbuf cross tools require', result.stdout)

    def test_configure_check_refuses_absent_query_config(self):
        for recipe, target in RECIPES:
            self.assertIn(target, bmake(recipe, '-V', '${.ALLTARGETS}').stdout.split(), recipe)
            for absent in ABSENT:
                with self.subTest(recipe=recipe, absent=absent):
                    result = bmake(recipe, *absent, target)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(MESSAGE, result.stdout + result.stderr)

    def test_configure_check_runs_first_in_pre_configure(self):
        for recipe, _target in RECIPES:
            with self.subTest(recipe=recipe):
                # -n prints the pre-configure commands without running them.
                result = bmake(recipe, *ABSENT[1], '-n', 'pre-configure')
                self.assertEqual(result.returncode, 0, result.stderr)
                message = result.stdout.find(MESSAGE)
                self.assertGreaterEqual(message, 0, 'pre-configure does not run the input check')
                for query in ('target-query.py', 'target-tools.py'):
                    position = result.stdout.find(query)
                    if position >= 0:
                        self.assertLess(message, position, 'the target query runs before the input check')

    def test_configure_check_accepts_an_existing_query_config(self):
        for recipe, target in RECIPES:
            with self.subTest(recipe=recipe):
                result = bmake(recipe, *self.valid, target)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


def main():
    global ARGS
    parser = argparse.ArgumentParser()
    parser.add_argument('--bmake', required=True)
    parser.add_argument('--pkgsrc', type=Path, required=True)
    parser.add_argument('--makeconf', type=Path, required=True)
    ARGS, rest = parser.parse_known_args()
    ARGS.pkgsrc = ARGS.pkgsrc.resolve()
    unittest.main(argv=[sys.argv[0], *rest])


if __name__ == '__main__':
    main()
