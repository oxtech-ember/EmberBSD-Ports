#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check that every overlay LICENSE token names a pkgsrc licence.

pkgsrc rejects an unknown licence name as an unacceptable licence
condition, even when the intended licence is accepted. A token is valid
when the pinned pkgsrc tree or the export provides licenses/NAME, or when
the recipe supplies the text through LICENSE_FILE.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
ASSIGNMENT = re.compile(r'^LICENSE[+?:]?=[ \t]*(.*)$', re.M)
OPERATORS = {'AND', 'OR'}


def known_licenses(root):
    names = {path.name for path in (root / 'upstream/pkgsrc/licenses').iterdir()}
    export = (root / 'pkgsrc/export.conf').read_text(encoding='utf-8')
    for line in export.splitlines():
        fields = line.split('\t')
        if len(fields) == 3 and fields[0] == 'file' and fields[2].startswith('licenses/'):
            names.add(fields[2][len('licenses/'):])
    return names


def unknown_tokens(root):
    known = known_licenses(root)
    found = []
    for makefile in sorted((root / 'pkgsrc').glob('*/*/Makefile*')):
        text = makefile.read_text(encoding='utf-8', errors='replace').replace('\\\n', ' ')
        custom = re.search(r'^LICENSE_FILE[+?:]?=', text, re.M) is not None
        for match in ASSIGNMENT.finditer(text):
            tokens = re.split(r'[\s()]+', match.group(1).split('#')[0])
            for token in tokens:
                if not token or token in OPERATORS or '$' in token or token in known:
                    continue
                if not custom:
                    found.append('%s: %s' % (makefile.relative_to(root), token))
    return found


class RecipeLicenseTest(unittest.TestCase):
    def test_overlay_licenses_exist(self):
        self.assertEqual(unknown_tokens(ROOT), [])

    def test_unknown_name_is_reported(self):
        # The previous modemmanager-headers spelling must fail this check.
        import tempfile
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'upstream/pkgsrc/licenses').mkdir(parents=True)
            (root / 'upstream/pkgsrc/licenses/gnu-gpl-v2').write_text('', encoding='utf-8')
            (root / 'pkgsrc/devel/example').mkdir(parents=True)
            (root / 'pkgsrc/export.conf').write_text('', encoding='utf-8')
            recipe = root / 'pkgsrc/devel/example/Makefile'
            recipe.write_text('LICENSE=\tgnu-gpl-v2-or-later AND gnu-gpl-v2\n', encoding='utf-8')
            self.assertEqual(unknown_tokens(root), ['pkgsrc/devel/example/Makefile: gnu-gpl-v2-or-later'])
            recipe.write_text('LICENSE=\tvendor-license\nLICENSE_FILE=\t${WRKSRC}/COPYING\n', encoding='utf-8')
            self.assertEqual(unknown_tokens(root), [])


if __name__ == '__main__':
    unittest.main()
