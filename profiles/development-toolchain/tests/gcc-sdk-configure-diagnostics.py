#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted). Exact source checks, no configure execution.
"""Check the common SDK diagnostic patch against an explicit GCC source."""
import argparse
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
PROFILE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROFILE / 'runtime/recipe/files'))
import sdk_source
arguments = sdk_source.arguments(sys.argv[1:])
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--gcc-source', type=Path, required=True)
options, remaining = parser.parse_known_args(arguments)
from emberbsd_sdk.errors import SDKError


def module(name):
    path = Path(__file__).with_name(name + '.py')
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


compare = module('darwin-compare-debug')
probe = module('darwin-build-config')
PATCH = PROFILE / 'patches/gcc-sdk-configure-diagnostics.patch'
ORIGINAL = (options.gcc_source / 'configure').read_text()
FIXED = compare.apply_source({'configure': ORIGINAL}, PATCH.read_text())['configure']
PATHS = ('/usr/bin/uname', '/bin/uname', '/bin/arch', '/usr/bin/arch',
         '/usr/convex/getsysinfo', '/usr/bin/hostinfo', '/bin/machine',
         '/usr/bin/oslevel', '/bin/universe')


def recipe(text):
    required = next(line for line in text.splitlines() if line.startswith('+.for _ember_gcc16_input in '))
    assert 'EMBERBSD_GCC16_UNAME' in required.split()
    assert '+CONFIGURE_ENV+= GCC_CONFIGURE_SDK=yes\n' in text
    assert '+CONFIGURE_ENV+= GCC_CONFIGURE_UNAME=${EMBERBSD_GCC16_UNAME:Q}\n' in text
    assert '+MAKE_ENV+= GCC_CONFIGURE_SDK=yes\n' in text
    assert '+MAKE_ENV+= GCC_CONFIGURE_UNAME=${EMBERBSD_GCC16_UNAME:Q}\n' in text
    assert '+CONFIGURE_ARGS+= --without-build-config\n' in text


class Diagnostics(unittest.TestCase):
    def check_source(self, text):
        with patch.object(Path, 'read_text', return_value=text):
            probe.check_configure_source(options.gcc_source)

    def test_exact_patch_preserves_all_other_configure_bytes(self):
        start = FIXED.index('# EmberBSD: explicit SDK diagnostics')
        end = FIXED.index('# hostname on some systems', start)
        restored = FIXED[:start] + FIXED[end:]
        for path in PATHS:
            call = '`(emberbsd_host_diagnostic ' + path
            self.assertEqual(restored.count(call), 1)
            restored = restored.replace(call, '`(' + path)
        self.assertEqual(restored, ORIGINAL)
        self.assertNotIn('bootstrap-debug', PATCH.read_text())

    def test_required_selector_guard_and_unset_route(self):
        body = FIXED[FIXED.index('# EmberBSD: explicit SDK diagnostics'):FIXED.index('# hostname on some systems')]
        self.assertIn('if test "${GCC_CONFIGURE_SDK+set}" = set; then', body)
        self.assertIn('if test "$GCC_CONFIGURE_SDK" != yes; then', body)
        self.assertIn('case ${GCC_CONFIGURE_UNAME-} in', body)
        self.assertIn('test ! -f "$GCC_CONFIGURE_UNAME" || test ! -x "$GCC_CONFIGURE_UNAME"', body)
        self.assertEqual(body.count('exit 1'), 3)
        function = body[body.index('emberbsd_host_diagnostic ()'):]
        self.assertIn('if test "${GCC_CONFIGURE_SDK-}" = yes; then', function)
        self.assertIn('/usr/bin/uname | /bin/uname)', function)
        self.assertIn('shift\n        "$GCC_CONFIGURE_UNAME" "$@"', function)
        self.assertIn("*) echo 'unavailable (selected SDK profile)' ;;", function)
        self.assertIn('else\n    "$@"\n  fi', function)

    def test_preflight_accepts_common_patch_and_refuses_legacy_mutations(self):
        self.check_source(FIXED)
        with self.assertRaises(SDKError):
            self.check_source(ORIGINAL)
        for path in PATHS:
            mutant = FIXED.replace('`(emberbsd_host_diagnostic ' + path, '`(' + path)
            with self.assertRaisesRegex(SDKError, 'unselected diagnostic'):
                self.check_source(mutant)
        with self.assertRaises(SDKError):
            self.check_source(FIXED.replace('emberbsd_host_diagnostic ()', 'unbound_function ()'))

    def test_common_recipe_and_missing_selector_controls(self):
        text = (PROFILE / 'patches/gcc-darwin-host.patch').read_text()
        recipe(text)
        for old, new in [(' EMBERBSD_GCC16_UNAME OSX_SDK_PATH', ' OSX_SDK_PATH'),
                         ('+CONFIGURE_ENV+= GCC_CONFIGURE_SDK=yes\n', ''),
                         ('+MAKE_ENV+= GCC_CONFIGURE_SDK=yes\n', ''),
                         ('${EMBERBSD_GCC16_UNAME:Q}', '/usr/bin/uname')]:
            self.assertIn(old, text)
            with self.assertRaises(AssertionError):
                recipe(text.replace(old, new))

    def test_common_export_owns_one_source_patch(self):
        row = ('recipe-patch\tprofiles/development-toolchain/patches/gcc-sdk-configure-diagnostics.patch'
               '\tlang/gcc16\tpatch-configure_sdk_diagnostics\n')
        self.assertEqual((PROFILE.parents[1] / 'pkgsrc/export.conf').read_text().count(row), 1)


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0], *remaining])
