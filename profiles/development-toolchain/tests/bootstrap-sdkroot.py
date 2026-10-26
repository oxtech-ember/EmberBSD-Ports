#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Execute the exported bootstrap's Darwin SDK selection without compiling."""

import argparse
from pathlib import Path
import subprocess
import tempfile
import unittest


class SDKSelection(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='bootstrap-sdkroot-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.sdk = self.root / 'native-sdk'
        (self.sdk / 'usr/include').mkdir(parents=True)
        (self.sdk / 'usr/lib').mkdir()
        xcrun = self.root / 'xcrun'
        xcrun.write_text('#!/bin/sh\nprintf "%s\\n" /discovered-sdk\n')
        xcrun.chmod(0o755)
        source = BOOTSTRAP.read_text().split('\nDarwin)\n', 1)[1]
        source = source.split('\n\tcheck_compiler=yes\n', 1)[1]
        source = source.split('\n\t# Combine major.minor product version', 1)[0]
        self.script = ('die() { printf "%s\\n" "$*" >&2; exit 1; }\n' +
                       source.replace('/usr/bin/xcrun', str(xcrun)) +
                       '\nprintf "%s\\n" "${CFLAGS}"\n')

    def select(self, sdk='', deployment='27.0', inherited_sdk=''):
        return subprocess.run([SHELL, '-c', self.script], text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env={'PATH': '/nonexistent', 'SDKROOT': str(sdk), 'SDK_PATH': inherited_sdk,
                 'MACOSX_DEPLOYMENT_TARGET': deployment, 'CFLAGS': '-O2'})

    def test_explicit_sdk_wins_over_deployment_discovery(self):
        result = self.select(self.sdk)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), f'-isysroot {self.sdk} -O2')

    def test_explicit_sdk_does_not_require_deployment(self):
        result = self.select(self.sdk, '')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), f'-isysroot {self.sdk} -O2')

    def test_invalid_explicit_sdk_fails_without_discovery(self):
        for sdk in ('relative-sdk', self.root / 'missing-sdk', self.root / 'SDK space',
                    self.root / 'SDK;other-command'):
            with self.subTest(sdk=sdk):
                result = self.select(sdk)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('SDKROOT', result.stderr)
                self.assertNotIn('/discovered-sdk', result.stdout)

    def test_unspecified_sdk_preserves_upstream_discovery(self):
        result = self.select()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), '-isysroot /discovered-sdk -O2')

    def test_no_sdk_or_deployment_preserves_flags(self):
        result = self.select('', '')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), '-O2')

    def test_inherited_sdk_path_does_not_enable_implicit_selection(self):
        result = self.select('', '', '/foreign-sdk')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), '-O2')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bootstrap', type=Path, required=True)
    parser.add_argument('--shell', type=Path, required=True)
    args = parser.parse_args()
    BOOTSTRAP = args.bootstrap.resolve(strict=True)
    SHELL = str(args.shell.resolve(strict=True))
    unittest.main(argv=[__file__])
