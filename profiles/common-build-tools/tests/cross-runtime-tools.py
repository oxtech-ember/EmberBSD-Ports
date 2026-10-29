#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). No target, SSH connection or download is used.
"""groff and automake do not request build-host runtime tools in cross builds.

pkgsrc refuses USE_TOOLS+=TOOL:run in a cross build, because the build-host
tool cannot run on the target. groff needs awk and sed at build time only on
a NetBSD target and the target Ghostscript package for grohtml. automake
needs the target m4 package instead of the build-host m4. Native builds keep
the original runtime tools.

Usage: cross-runtime-tools.py --bmake BMAKE --pkgsrc TREE --makeconf CROSS_MAKECONF
"""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import unittest

ARGS = None
REFUSAL = 'USE_TOOLS+={} not supported in cross-compilation'


def query(recipe, *names, native=False):
    command = [ARGS.bmake, '-C', str(ARGS.pkgsrc / recipe), f'MAKECONF={ARGS.makeconf}']
    if native:
        command.append('USE_CROSS_COMPILE=no')
    for name in names:
        command += ['-V', '${' + name + '}']
    result = subprocess.run(command, capture_output=True, text=True, timeout=300,
                            env=dict(os.environ, LC_ALL='C'))
    if result.returncode:
        raise AssertionError(result.stderr)
    return dict(zip(names, result.stdout.splitlines()))


class CrossRuntimeTools(unittest.TestCase):
    def test_real_cross_configuration(self):
        values = query('textproc/groff', 'USE_CROSS_COMPILE', 'OPSYS')
        self.assertEqual(values['USE_CROSS_COMPILE'], 'yes')
        self.assertEqual(values['OPSYS'], 'NetBSD')

    def test_groff_uses_awk_and_sed_on_the_build_host_only(self):
        values = query('textproc/groff', 'PKG_FAIL_REASON', 'USE_TOOLS')
        for tool in ('awk:run', 'sed:run'):
            self.assertNotIn(REFUSAL.format(tool), values['PKG_FAIL_REASON'])
            self.assertNotIn(tool, values['USE_TOOLS'].split())
        for tool in ('awk', 'sed'):
            self.assertIn(tool, values['USE_TOOLS'].split())

    def test_groff_documentation_uses_target_ghostscript(self):
        values = query('textproc/groff', 'PKG_OPTIONS', 'PKG_FAIL_REASON', 'USE_TOOLS',
                       'CONFIGURE_ARGS', 'DEPENDS')
        self.assertIn('groff-docs', values['PKG_OPTIONS'].split())
        self.assertNotIn(REFUSAL.format('gs:run'), values['PKG_FAIL_REASON'])
        self.assertNotIn('gs:run', values['USE_TOOLS'].split())
        self.assertIn('gs', values['USE_TOOLS'].split())
        self.assertIn('--with-gs=gs', values['CONFIGURE_ARGS'].split())
        self.assertTrue(any(d.startswith('ghostscript>=') and d.endswith(':../../print/ghostscript')
                            for d in values['DEPENDS'].split()), values['DEPENDS'])

    def test_automake_depends_on_target_m4(self):
        values = query('devel/automake', 'PKG_FAIL_REASON', 'USE_TOOLS', 'DEPENDS')
        self.assertNotIn(REFUSAL.format('gm4:run'), values['PKG_FAIL_REASON'])
        self.assertNotIn('gm4:run', values['USE_TOOLS'].split())
        self.assertIn('m4>=1.4:../../devel/m4', values['DEPENDS'].split())

    def test_native_builds_keep_runtime_tools(self):
        groff = query('textproc/groff', 'USE_TOOLS', native=True)['USE_TOOLS'].split()
        self.assertIn('awk:run', groff)
        self.assertIn('sed:run', groff)
        self.assertIn('gs:run', groff)
        automake = query('devel/automake', 'USE_TOOLS', native=True)['USE_TOOLS'].split()
        self.assertIn('gm4:run', automake)


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
