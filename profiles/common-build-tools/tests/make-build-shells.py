#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD; AI-assisted source checks for the shared make recipes.
"""Check a prepared pkgsrc export as data. Do not run a compiler or configure."""

import argparse
from pathlib import Path
import re
import sys
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
EXPORT = None
PATCH = 'profiles/common-build-tools/patches/pkgsrc-make-build-shells.patch'


def machine_commands(text):
    """Read the three literal command substitutions in the machine probes."""
    commands = re.findall(r'`([^`\n]*machine\.sh[^`\n]*)`', text)
    expected = ['"$SHELL" "$srcdir/machine.sh"',
                '"$SHELL" "$srcdir/machine.sh" arch',
                '"$SHELL" "$srcdir/machine.sh"']
    if commands != expected:
        raise ValueError('A machine probe bypasses the selected shell')
    return commands


def installer_files(text):
    matches = re.findall(r'^REPLACE_SH\+=\s*(.*)$', text, re.M)
    if [word for row in matches for word in row.split()] != ['build-aux/install-sh']:
        raise ValueError('The build installer lacks its shell replacement')
    if text.index('REPLACE_SH+=') > text.index('.include "../../mk/bsd.pkg.mk"'):
        raise ValueError('The replacement is defined after configure hooks')


class BuildShellTests(unittest.TestCase):
    def read(self, name):
        return (EXPORT / name).read_text()

    def test_bmake_calls_preserve_probe_arguments(self):
        machine = self.read('devel/bmake/files/machine.sh')
        self.assertEqual(machine.splitlines()[0], ':')
        for name in ('configure', 'configure.in'):
            text = self.read('devel/bmake/files/' + name)
            self.assertEqual(len(machine_commands(text)), 3)
            self.assertIn('machine=${machine:-`', text)
            self.assertIn('machine_arch=${machine_arch:-`', text)
            self.assertIn('generic) machine=`', text)
            self.assertIn('*)     machine=$with_machine;;', text)

    def test_bmake_mutations_are_rejected(self):
        for name in ('configure', 'configure.in'):
            text = self.read('devel/bmake/files/' + name)
            for changed in (text.replace('`"$SHELL" "$srcdir/machine.sh"', '`"$srcdir/machine.sh"', 1),
                            text.replace('`"$SHELL" "$srcdir/machine.sh"', '`/bin/sh "$srcdir/machine.sh"', 1),
                            text.replace('machine.sh" arch', 'machine.sh"', 1)):
                with self.subTest(name=name, changed=changed[:50]):
                    with self.assertRaisesRegex(ValueError, 'bypasses'):
                        machine_commands(changed)

    def test_gmake_uses_the_common_pre_configure_hook(self):
        installer_files(self.read('devel/gmake/Makefile'))
        hook = self.read('mk/configure/replace-interpreter.mk')
        self.assertIn('do-configure-pre-hook: replace-interpreter', hook)
        self.assertRegex(hook, r'(?m)^REPLACE\.sys-sh\.new=\s*\$\{SH\}$')
        self.assertRegex(hook, r'(?m)^REPLACE_FILES\.sys-sh=\s*\$\{REPLACE_SH\}$')
        # The recipe has no target OS or bootstrap condition around this hook.
        recipe = self.read('devel/gmake/Makefile')
        head = recipe[:recipe.index('REPLACE_SH+=')]
        self.assertNotRegex(head, r'(?m)^\.\s*(if|ifdef|ifndef)\b')

    def test_installer_mutations_are_rejected(self):
        text = self.read('devel/gmake/Makefile')
        for changed in (text.replace('REPLACE_SH+=', 'REPLACE_BASH+='),
                        text.replace('build-aux/install-sh', 'build-aux/missing')):
            with self.assertRaisesRegex(ValueError, 'lacks'):
                installer_files(changed)

    def test_perl_stays_test_only_and_missing_perl_is_guarded(self):
        recipe = self.read('devel/gmake/Makefile')
        self.assertRegex(recipe, r'(?m)^USE_TOOLS\+=\s*perl:test$')
        self.assertNotRegex(recipe, r'(?m)^(?:BOOTSTRAP_|BUILD_|TOOL_)?DEPENDS.*perl')
        guard = self.read('mk/tools/perl.mk')
        self.assertRegex(guard, r'(?m)^TOOLS_FAIL\+=\s*perl$')
        self.assertRegex(guard, r'(?m)^TOOLS_PATH\.perl=\s*\$\{TOOLS_CMD\.perl\}$')
        variables = self.read('lang/perl5/vars.mk')
        self.assertIn('.if defined(PERL5) && exists(${PERL5:Q})', variables)
        self.assertLess(variables.index('exists(${PERL5:Q})'),
                        variables.index('_PERL5_VARS_CMD='))
        provider = self.read('mk/tools/replace.mk')
        self.assertIn('.if !empty(USE_TOOLS:M${_ember_role}\\:test)\n'
                      'TEST_DEPENDS+= ${_ember_pattern}:../../${_ember_package}', provider)

    def test_export_order_and_scope(self):
        order = (ROOT / 'pkgsrc/export.conf').read_text()
        record = 'patch\t' + PATCH + '\n'
        self.assertEqual(order.count(record), 1)
        self.assertLess(order.index('pkgsrc-bmake-20260912.patch'), order.index(record))
        patch = (ROOT / PATCH).read_text()
        self.assertEqual(re.findall(r'^\+\+\+ b/(.*)$', patch, re.M),
            ['devel/gmake/Makefile', 'devel/bmake/files/configure',
             'devel/bmake/files/configure.in'])
        self.assertNotIn('EMBERBSD_NETBSD_BOOTSTRAP', patch)
        self.assertNotIn('USE_CROSS_COMPILE', patch)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--export', type=Path, required=True)
    args = parser.parse_args()
    EXPORT = args.export.resolve(strict=True)
    unittest.main(argv=[sys.argv[0]])
