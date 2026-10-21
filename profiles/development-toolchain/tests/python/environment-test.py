#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; real producer environment and host compiler contracts.
import sys
sys.dont_write_bytecode = True
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

PROFILE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROFILE / 'runtime/recipe/files'))
import sdk_source
ARGS = sdk_source.arguments(sys.argv[1:])
sys.path.insert(0, str(PROFILE))
import host
from emberbsd_sdk.errors import SDKError


class EnvironmentTest(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory(prefix='gcc-environment-')
        self.addCleanup(self.work.cleanup)
        self.root = Path(self.work.name)
        self.sdk = self.root / 'selected SDK'
        self.sdk.mkdir()

    def test_darwin_inherits_selected_sdk_but_not_ambient_configuration(self):
        with patch.object(host.platform, 'system', return_value='Darwin'), patch.dict(os.environ, {'SDKROOT': str(self.sdk), 'CONFIG_SITE': '/unused/site', 'FIXTURE_SECRET': 'excluded'}):
            env = host.environment()
        self.assertEqual(env['SDKROOT'], str(self.sdk))
        self.assertNotIn('CONFIG_SITE', env)
        self.assertNotIn('FIXTURE_SECRET', env)

    def test_linux_does_not_inherit_darwin_sdk(self):
        with patch.object(host.platform, 'system', return_value='Linux'), patch.dict(os.environ, {'SDKROOT': str(self.sdk)}):
            self.assertNotIn('SDKROOT', host.environment())

    def test_explicit_values_override_inheritance_and_keep_unset_available(self):
        selected = self.root / 'override'; selected.mkdir()
        with patch.object(host.platform, 'system', return_value='Darwin'), patch.dict(os.environ, {'SDKROOT': 'invalid-relative'}):
            self.assertEqual(host.environment({'SDKROOT': str(selected), 'CFLAGS': '-O2'})['SDKROOT'], str(selected))
            self.assertEqual(host.environment({'SDKROOT': ''})['SDKROOT'], '')
        with patch.object(host.platform, 'system', return_value='Linux'):
            self.assertEqual(host.environment({'SDKROOT': 'explicit-caller-value'})['SDKROOT'], 'explicit-caller-value')

    def test_invalid_selected_darwin_sdk_fails_before_launch(self):
        regular = self.root / 'file'; regular.write_text('not a directory')
        for value in ('relative', str(self.root / 'missing'), str(regular)):
            with self.subTest(value=value), patch.object(host.platform, 'system', return_value='Darwin'), patch.dict(os.environ, {'SDKROOT': value}), self.assertRaisesRegex(SDKError, 'SDKROOT'):
                host.environment()

    def test_real_capture_and_logged_child_receive_selected_environment(self):
        child = 'import os; assert "CONFIG_SITE" not in os.environ; assert "FIXTURE_SECRET" not in os.environ; print(os.environ["SDKROOT"])'
        with patch.object(host.platform, 'system', return_value='Darwin'), patch.dict(os.environ, {'SDKROOT': str(self.sdk), 'CONFIG_SITE': '/unused/site', 'FIXTURE_SECRET': 'excluded'}):
            self.assertEqual(host.capture([sys.executable, '-c', child]), str(self.sdk) + '\n')
            log = self.root / 'child.log'
            host.logged([sys.executable, '-c', child], log)
            self.assertEqual(log.read_text(), str(self.sdk) + '\n')

    @unittest.skipUnless(sys.platform == 'darwin', 'Darwin SDK and GCC16 link contract')
    def test_real_gcc16_links_through_capture_and_logged(self):
        cc = shutil.which('gcc-16')
        self.assertIsNotNone(cc, 'GCC16 is required for this host contract')
        sdk = subprocess.check_output(['xcrun', '--show-sdk-path'], text=True).strip()
        source = self.root / 'probe.c'
        source.write_text('#include <stdio.h>\nint main(void) { puts("host SDK link passed"); return 0; }\n')
        with patch.dict(os.environ, {'SDKROOT': sdk, 'CONFIG_SITE': '/unused/site', 'FIXTURE_SECRET': 'excluded'}):
            self.assertTrue(host.capture([cc, '-dumpfullversion']).startswith('16.'))
            for runner in ('capture', 'logged'):
                binary = self.root / runner
                argv = [cc, str(source), '-o', str(binary)]
                if runner == 'capture':
                    host.capture(argv)
                else:
                    host.logged(argv, self.root / 'compile.log')
                self.assertEqual(host.capture([binary]), 'host SDK link passed\n')


unittest.main(argv=[sys.argv[0]] + ARGS)
