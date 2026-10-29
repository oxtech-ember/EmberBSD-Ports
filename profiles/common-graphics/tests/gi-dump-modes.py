#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). No target, SSH connection or download is used.
"""Cross recipes replay stored GI dumps unless a live target is selected.

The default mode is replay from the recipe's files/gi-dump/PLATFORM, and it
needs no GI query configuration. Live and capture modes need one, capture
also an existing capture directory, and recipes that execute target programs
(EMBERBSD_GI_EXECUTE=yes) need one in every mode. The dump identity reaches
the launcher through MAKE_ENV (and CONFIGURE_ENV for WebKit's CMake).

Usage: gi-dump-modes.py --bmake BMAKE --pkgsrc TREE --makeconf CROSS_MAKECONF
"""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ARGS = None
DUMP_ONLY = ('devel/pango', 'fonts/harfbuzz')
QUERY_MESSAGE = 'EMBERBSD_GI_QUERY_CONFIG must name an existing absolute file without shell metacharacters'
CAPTURE_MESSAGE = 'EMBERBSD_GI_DUMP_CAPTURE_DIR must name an existing absolute directory'


def bmake(recipe, *args):
    return subprocess.run([ARGS.bmake, '-C', str(ARGS.pkgsrc / recipe), f'MAKECONF={ARGS.makeconf}', *args],
                          capture_output=True, text=True, timeout=300, env=dict(os.environ, LC_ALL='C'))


def value(recipe, expression, *args):
    result = bmake(recipe, *args, '-V', expression)
    if result.returncode != 0:
        raise AssertionError(result.stderr)
    return result.stdout.strip()


class DumpModes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        root = Path(cls.temp.name)
        (root / 'query.json').write_text('{}\n')
        cls.query = 'EMBERBSD_GI_QUERY_CONFIG=' + str(root / 'query.json')
        cls.capture = 'EMBERBSD_GI_DUMP_CAPTURE_DIR=' + str(root)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_default_replays_the_recipe_dump_directory(self):
        for recipe in DUMP_ONLY:
            with self.subTest(recipe=recipe):
                platform = value(recipe, '${CROSS_OPSYS}-${CROSS_OS_VERSION}-${MACHINE_ARCH}')
                self.assertRegex(platform, r'^NetBSD-[0-9.]+-[a-z0-9_]+$')
                self.assertEqual(value(recipe, '${EMBERBSD_GI_DUMP_MODE}'), 'replay')
                self.assertEqual(value(recipe, '${EMBERBSD_GI_DUMP_DIR}'),
                                 str(ARGS.pkgsrc / recipe / 'files' / 'gi-dump' / platform))
                env = value(recipe, '${MAKE_ENV}').split()
                for item in ('EMBERBSD_GI_DUMP_MODE=replay', f'EMBERBSD_GI_DUMP_PLATFORM={platform}',
                             f'EMBERBSD_GI_DUMP_RECIPE={recipe}'):
                    self.assertIn(item, env)
                package = value(recipe, '${PKGNAME_NOREV}')
                self.assertIn(f'EMBERBSD_GI_DUMP_PACKAGE={package}', env)

    def test_replay_needs_no_query_configuration(self):
        for recipe in DUMP_ONLY:
            with self.subTest(recipe=recipe):
                result = bmake(recipe, 'emberbsd-gi-inputs')
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(value(recipe, '${PKG_FAIL_REASON}'), '')

    def test_replay_checks_dumps_instead_of_the_target(self):
        for recipe in DUMP_ONLY:
            with self.subTest(recipe=recipe):
                replay = bmake(recipe, '-n', 'emberbsd-gi-native')
                self.assertEqual(replay.returncode, 0, replay.stderr)
                self.assertIn('No stored GI dumps for', replay.stdout)
                self.assertNotIn('target-query.py --check', replay.stdout)
                live = bmake(recipe, 'EMBERBSD_GI_DUMP_MODE=live', self.query, '-n', 'emberbsd-gi-native')
                self.assertEqual(live.returncode, 0, live.stderr)
                self.assertIn('target-query.py --check', live.stdout)

    def test_missing_dump_directory_refuses_replay(self):
        result = bmake('devel/pango', 'EMBERBSD_GI_DUMP_DIR=/ember-missing-gi-dumps', 'emberbsd-gi-native')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('No stored GI dumps for', result.stdout + result.stderr)

    def test_live_and_capture_need_a_query_configuration(self):
        for mode in ('live', 'capture'):
            with self.subTest(mode=mode):
                result = bmake('devel/pango', f'EMBERBSD_GI_DUMP_MODE={mode}', self.capture, 'emberbsd-gi-inputs')
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(QUERY_MESSAGE, result.stdout + result.stderr)
                accepted = bmake('devel/pango', f'EMBERBSD_GI_DUMP_MODE={mode}', self.capture, self.query,
                                 'emberbsd-gi-inputs')
                self.assertEqual(accepted.returncode, 0, accepted.stdout + accepted.stderr)

    def test_capture_needs_an_existing_capture_directory(self):
        for directory in ((), ('EMBERBSD_GI_DUMP_CAPTURE_DIR=/ember-missing-capture',),
                          ('EMBERBSD_GI_DUMP_CAPTURE_DIR=relative',)):
            with self.subTest(directory=directory):
                result = bmake('devel/pango', 'EMBERBSD_GI_DUMP_MODE=capture', self.query, *directory,
                               'emberbsd-gi-inputs')
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(CAPTURE_MESSAGE, result.stdout + result.stderr)

    def test_invalid_mode_is_refused(self):
        result = bmake('devel/pango', 'EMBERBSD_GI_DUMP_MODE=record', self.query, 'emberbsd-gi-inputs')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('EMBERBSD_GI_DUMP_MODE must be replay, live or capture', result.stdout + result.stderr)

    def test_target_execution_needs_a_query_in_replay(self):
        self.assertEqual(value('graphics/gdk-pixbuf2', '${EMBERBSD_GI_EXECUTE}'), 'yes')
        result = bmake('graphics/gdk-pixbuf2', 'emberbsd-gi-inputs')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(QUERY_MESSAGE, result.stdout + result.stderr)

    def test_webkit_cmake_receives_the_dump_identity(self):
        env = value('www/webkit-gtk41', '${CONFIGURE_ENV}').split()
        self.assertIn('EMBERBSD_GI_DUMP_MODE=replay', env)
        self.assertIn('EMBERBSD_GI_DUMP_RECIPE=www/webkit-gtk41', env)


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
