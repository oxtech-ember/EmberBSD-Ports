#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted dependency revision check regressions.
"""Subprocess checks for scripts/check-cross-revisions.py."""
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
SCRIPT = SCRIPTS / 'check-cross-revisions.py'
CROSS = '.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && ${OPSYS} == "NetBSD"'

# A shared Makefile with a cross-only revision and a wrapper SDK package,
# like textproc/icu and textproc/icu-devel.
ICU = {
    'textproc/icu/Makefile': f'''
        DISTNAME=	icu4c-78.3-src
        PKGNAME=	${{DISTNAME:S/4c//:S/-src//}}
        .if defined(EMBERBSD_ICU_DEVEL)
        PKGNAME=	icu-devel-78.3
        .endif
        {CROSS}
        PKGREVISION= 4
        .endif
        ''',
    'textproc/icu-devel/Makefile': '''
        EMBERBSD_ICU_DEVEL= yes
        .include "../../textproc/icu/Makefile"
        .if ${USE_CROSS_COMPILE:Uno:tl} != "yes" || ${OPSYS} != "NetBSD"
        PKG_FAIL_REASON+= "cross only"
        .endif
        ''',
}


def run(files):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / 'pkgsrc'
        for name, text in files.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(textwrap.dedent(text).lstrip())
        result = subprocess.run([sys.executable, str(SCRIPT), str(root)],
                                capture_output=True, text=True)
        return result.returncode, result.stdout.replace(str(root) + '/', '')


def with_bl3(pin, extra=None):
    files = dict(ICU)
    files['textproc/icu-devel/buildlink3.mk'] = (
        'BUILDLINK_API_DEPENDS.icu-devel+= %s\n' % pin)
    files.update(extra or {})
    return files


class CrossRevisionTest(unittest.TestCase):
    def test_exact_pin_on_conditional_revision(self):
        # The next2 pass: icu-devel-78.3nb4 was built and the exact pin
        # still named nb3, so every icu-devel consumer rebuilt it in place.
        status, out = run(with_bl3('icu-devel-78.3nb3'))
        self.assertEqual(status, 1)
        self.assertIn('exact pattern icu-devel-78.3nb3 on textproc/icu-devel', out)
        status, out = run(with_bl3('icu-devel-78.3nb4'))
        self.assertEqual(status, 1, 'an exact pin breaks at the next bump')

    def test_minimum_pin_against_cross_revision(self):
        self.assertEqual(run(with_bl3('icu-devel>=78.3nb4'))[0], 0)
        status, out = run(with_bl3('icu-devel>=78.3nb5'))
        self.assertEqual(status, 1)
        self.assertIn('needs nb5 but the cross build of textproc/icu-devel '
                      'has PKGREVISION 4', out)

    def test_unconditional_pattern_checks_each_build(self):
        consumer = {'misc/consumer/Makefile': 'DEPENDS+= icu>=78.3nb4:../../textproc/icu\n'}
        status, out = run(with_bl3('icu-devel>=78.3nb4', consumer))
        self.assertEqual(status, 1)
        self.assertIn('the native build of textproc/icu has PKGREVISION 0', out)
        self.assertNotIn('cross build of textproc/icu ', out)

    def test_tool_depends_is_native(self):
        tool = {'misc/consumer/Makefile': f'''
            {CROSS}
            TOOL_DEPENDS+= icu>=78.3nb1:../../textproc/icu
            BUILD_DEPENDS+= icu>=78.3nb4:../../textproc/icu
            .endif
            '''}
        status, out = run(with_bl3('icu-devel>=78.3nb4', tool))
        self.assertEqual(status, 1)
        self.assertEqual(out.count('needs'), 1, out)
        self.assertIn('icu>=78.3nb1 needs nb1 but the native build', out)

    def test_later_assignment_wins(self):
        files = {
            'x11/qt/Makefile': f'''
                PKGNAME= qt-6.12.0
                PKGREVISION= 13
                {CROSS}
                PKGREVISION= 6
                .endif
                ''',
            'x11/qt/buildlink3.mk': f'''
                {CROSS}
                BUILDLINK_API_DEPENDS.qt+= qt>=6.12.0nb8
                .else
                BUILDLINK_API_DEPENDS.qt+= qt>=6.12.0nb13
                .endif
                ''',
        }
        status, out = run(files)
        self.assertEqual(status, 1)
        self.assertIn('qt>=6.12.0nb8 needs nb8 but the cross build of x11/qt '
                      'has PKGREVISION 6', out)
        self.assertNotIn('nb13 needs', out)

    def test_other_version_is_left_alone(self):
        files = {
            'textproc/enchant2/Makefile': 'DISTNAME= enchant-2.8.21\n'
                                          'PKGNAME= ${DISTNAME:S/enchant/enchant2/}\n'
                                          'PKGREVISION= 1\n',
            'textproc/enchant2/buildlink3.mk':
                'BUILDLINK_ABI_DEPENDS.enchant2+= enchant2>=2.8.19nb2\n',
        }
        self.assertEqual(run(files), (0, ''))
        files['textproc/enchant2/buildlink3.mk'] = \
            'BUILDLINK_ABI_DEPENDS.enchant2+= enchant2>=2.8.21nb2\n'
        self.assertEqual(run(files)[0], 1)

    def test_ports_tree(self):
        tree = SCRIPTS.parent / 'pkgsrc'
        result = subprocess.run([sys.executable, str(SCRIPT), str(tree)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
