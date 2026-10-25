#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted). Exact source checks, no configure execution.
"""Check the common SDK diagnostic patch against an explicit GCC source."""
import argparse
import importlib.util
import hashlib
import tarfile
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
inputs = parser.add_mutually_exclusive_group(required=True)
inputs.add_argument('--gcc-source', type=Path)
inputs.add_argument('--gcc-archive', type=Path)
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
ROSTER = (PROFILE / 'patches/gcc-sdk-configure-diagnostics.files').read_text().splitlines()
HELPER = 'config/emberbsd-sdk-diagnostics.sh'
assert ROSTER == sorted(set(ROSTER)) and len(ROSTER) == 34
if options.gcc_archive:
    expected = next(row.split('\t')[3] for row in (PROFILE / 'sources.tsv').read_text().splitlines()
                    if row.startswith('gcc\t16.2.0\t'))
    with options.gcc_archive.open('rb') as stream:
        assert hashlib.file_digest(stream, 'sha256').hexdigest() == expected
    ORIGINAL = {}
    with tarfile.open(options.gcc_archive) as archive:
        for member in archive:
            if member.isfile() and member.name.endswith('/configure'):
                raw = archive.extractfile(member).read().decode()
                if '`(/usr/bin/uname' in raw:
                    ORIGINAL[member.name.split('/', 1)[1]] = raw
else:
    ORIGINAL = {str(p.relative_to(options.gcc_source)): p.read_text()
                for p in options.gcc_source.rglob('configure') if p.is_file()}
    ORIGINAL = {p: s for p, s in ORIGINAL.items() if '`(/usr/bin/uname' in s}
assert set(ORIGINAL) == set(ROSTER), 'Canonical configure roster differs from the complete source'
FIXED = compare.apply_source({**ORIGINAL, HELPER: ''}, PATCH.read_text())
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
    def check_source(self, contents):
        root = Path('/nonexecuted/source-fixture')
        def read(path, *args, **kwargs):
            if path.name == 'gcc-sdk-configure-diagnostics.files':
                return '\n'.join(ROSTER) + '\n'
            relative = str(path.relative_to(root))
            if relative not in contents:
                raise FileNotFoundError(relative)
            return contents[relative]
        with patch.object(Path, 'read_text', read):
            probe.check_configure_source(root)

    def test_exact_patch_preserves_all_other_configure_bytes(self):
        for name in ROSTER:
            text = FIXED[name]
            start = text.index('# EmberBSD: selected SDK diagnostic entry.')
            end = text.index('cat <<_ASUNAME', start)
            restored = text[:start] + text[end:]
            for path in PATHS:
                call = '`(emberbsd_host_diagnostic ' + path
                self.assertEqual(restored.count(call), 1, name)
                restored = restored.replace(call, '`(' + path)
            self.assertEqual(restored, ORIGINAL[name], name)
        self.assertEqual(set(FIXED), set(ROSTER) | {HELPER})
        self.assertNotIn('bootstrap-debug', PATCH.read_text())

    def test_one_shared_helper_and_correct_nested_source_paths(self):
        self.assertEqual(tuple(ROSTER), probe.CONFIGURE_FILES)
        helper = FIXED[HELPER]
        self.assertIn('if test "$GCC_CONFIGURE_SDK" != yes; then', helper)
        self.assertIn('case ${GCC_CONFIGURE_UNAME-} in', helper)
        self.assertIn('test ! -f "$GCC_CONFIGURE_UNAME" || test ! -x "$GCC_CONFIGURE_UNAME"', helper)
        self.assertEqual(helper.count('exit 1'), 3)
        self.assertIn('/usr/bin/uname | /bin/uname)', helper)
        self.assertIn('shift\n      "$GCC_CONFIGURE_UNAME" "$@"', helper)
        self.assertIn("*) echo 'unavailable (selected SDK profile)' ;;", helper)
        for name in ROSTER:
            relative = '../' * (len(Path(name).parts) - 1) + HELPER
            hook = FIXED[name].split('# EmberBSD: selected SDK diagnostic entry.\n', 1)[1].split('cat <<_ASUNAME', 1)[0]
            self.assertIn('if test "${GCC_CONFIGURE_SDK+set}" = set; then', hook)
            self.assertIn('. "${srcdir}/' + relative + '" || exit 1', hook)
            self.assertIn('emberbsd_host_diagnostic () { "$@"; }', hook)
            self.assertNotIn('case $1', hook)

    def test_preflight_refuses_unpatched_nested_source_and_bad_helper(self):
        self.check_source(FIXED)
        for name in ROSTER:
            with self.subTest(source=name), self.assertRaises(SDKError):
                self.check_source({**FIXED, name: ORIGINAL[name]})
            with self.subTest(missing=name), self.assertRaises(SDKError):
                self.check_source({p: value for p, value in FIXED.items() if p != name})
        for path in PATHS:
            mutant = dict(FIXED)
            mutant['gcc/configure'] = mutant['gcc/configure'].replace('`(emberbsd_host_diagnostic ' + path, '`(' + path)
            with self.assertRaisesRegex(SDKError, 'unselected diagnostic'):
                self.check_source(mutant)
        with self.assertRaises(SDKError):
            self.check_source({**FIXED, HELPER: 'not the diagnostic helper'})

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
