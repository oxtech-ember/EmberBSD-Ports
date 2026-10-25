#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD; AI-assisted source checks for the canonical BSD installer.
"""Check the fixed BSD install source contract without executing native tools."""

import json
from pathlib import Path
import re
import sys
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
PATCH = ROOT / 'profiles/common-build-tools/patches/pkgsrc-bsdinstall-native-shell.patch'
PROFILE = ROOT / 'profiles/common-build-tools/bootstrap/bsdinstall.json'
RECIPE = 'sysutils/bsdinstall/Makefile'
PROGRAM = 'sysutils/bsdinstall/files/bsdinstall.c'
SOURCE = ROOT / 'upstream/pkgsrc'


def replay(originals, patch):
    """Match these finite source hunks at their exact original line numbers."""
    lines = patch.splitlines(keepends=True)
    result = {}
    i = 0
    while i < len(lines):
        if not lines[i].startswith('--- a/'):
            i += 1
            continue
        name = lines[i][6:].rstrip('\n')
        if name not in originals or lines[i + 1] != '+++ b/' + name + '\n':
            raise ValueError('Unexpected source target')
        before = originals[name].splitlines(keepends=True)
        output, cursor = [], 0
        i += 2
        while i < len(lines) and lines[i].startswith('@@ '):
            match = re.fullmatch(r'@@ -(\d+),(\d+) \+(\d+),(\d+) @@\n', lines[i])
            if not match:
                raise ValueError('Unsupported hunk')
            start, old_count, _, new_count = map(int, match.groups())
            start -= 1
            if start < cursor:
                raise ValueError('Overlapping hunk')
            output.extend(before[cursor:start])
            cursor = start
            old, new = [], []
            i += 1
            while i < len(lines) and lines[i][:1] in (' ', '+', '-'):
                line = lines[i]
                if line.startswith('--- a/'):
                    break
                if line[0] in ' -':
                    old.append(line[1:])
                if line[0] in ' +':
                    new.append(line[1:])
                i += 1
            if len(old) != old_count or len(new) != new_count:
                raise ValueError('Hunk counts differ')
            if before[cursor:cursor + old_count] != old:
                raise ValueError('Exact source context differs')
            output.extend(new)
            cursor += old_count
        output.extend(before[cursor:])
        result[name] = ''.join(output)
    if set(result) != set(originals):
        raise ValueError('Incomplete source patch')
    return result


class SourceTests(unittest.TestCase):
    def setUp(self):
        self.original = {name: (SOURCE / name).read_text() for name in (RECIPE, PROGRAM)}
        self.patch = PATCH.read_text()
        self.result = replay(self.original, self.patch)
        self.profile = json.loads(PROFILE.read_text())

    def test_exact_source_delta_and_default(self):
        anchor = '#ifdef SUPPORT_MTREE\n#include "mtree.h"\n#endif\n'
        expected = self.original[PROGRAM].replace(anchor, anchor +
            '\n#ifndef EMBERBSD_BSDINSTALL_SHELL\n'
            '#define EMBERBSD_BSDINSTALL_SHELL _PATH_BSHELL\n#endif\n')
        expected = expected.replace('execl(_PATH_BSHELL, "sh", "-c", cmd, NULL);',
            'execl(EMBERBSD_BSDINSTALL_SHELL, "sh", "-c", cmd, NULL);')
        self.assertEqual(self.result[PROGRAM], expected)
        self.assertEqual(expected.count('execl(EMBERBSD_BSDINSTALL_SHELL,'), 2)
        self.assertNotIn('execl(EMBERBSD_BSDINSTALL_SHELL,', self.original[PROGRAM])
        self.assertIn('execlp(stripprog, "strip", to_name, NULL);', expected)

    def test_recipe_opt_in_does_not_change_strip_or_other_flags(self):
        addition = ('\n# Bind child shells only for an explicit initial native producer.\n'
            '.if defined(EMBERBSD_BSDINSTALL_SHELL)\n'
            'CPPFLAGS+=\t-DEMBERBSD_BSDINSTALL_SHELL=\\"${EMBERBSD_BSDINSTALL_SHELL:Q}\\"\n'
            '.endif\n')
        self.assertEqual(self.result[RECIPE].replace(addition, ''), self.original[RECIPE])
        self.assertIn('-DTARGET_STRIP=\\"${TOOLS_PLATFORM.strip:Q}\\"', self.result[RECIPE])

    def test_changed_source_context_refuses(self):
        changed = dict(self.original)
        changed[PROGRAM] = changed[PROGRAM].replace(
            '#include "mtree.h"', '#include "changed-mtree.h"')
        with self.assertRaisesRegex(ValueError, 'Exact source context differs'):
            replay(changed, self.patch)

    def test_export_registers_one_canonical_patch(self):
        record = 'patch\t' + PATCH.relative_to(ROOT).as_posix() + '\n'
        self.assertEqual((ROOT / 'pkgsrc/export.conf').read_text().count(record), 1)
        self.assertEqual(set(self.result), {RECIPE, PROGRAM})

    def test_fixed_two_source_and_selected_input_contract(self):
        p = self.profile
        self.assertEqual(p['sources'], [PROGRAM, 'sysutils/bsdinstall/files/setmode.c'])
        self.assertEqual(p['required_tool_roles'], ['cc', 'sh', 'strip'])
        self.assertEqual(p['compiler'], dict(family='gcc', major=16, abi='native'))
        self.assertEqual(p['cppflags'], ['-DHAVE_NBCOMPAT_H=1', '-D_PATH_DEVNULL="/dev/null"'])
        self.assertEqual(p['selected_defines'], dict(EMBERBSD_BSDINSTALL_SHELL='sh', TARGET_STRIP='strip'))
        self.assertEqual(p['compat'], dict(recipe='pkgtools/libnbcompat',
            include_dir='include', static_library='lib/libnbcompat.a'))
        self.assertEqual((p['headers'], p['cflags'], p['link_flags'], p['libraries']), ([], [], [], []))
        self.assertTrue(p['initial_only'])

    def test_cases_keep_errors_and_child_routes(self):
        cases = {case['name']: case for case in self.profile['runtime_cases']}
        self.assertEqual(len(cases), 19)
        self.assertEqual(self.profile['files'], {'input.txt': 'payload\n'})
        for name in ('same-file', 'missing-file', 'invalid-mode', 'invalid-option',
                     'metalog-unsupported', 'privileged-unknown-owner',
                     'failed-after-hook', 'directory-strip-refused', 'missing-operands'):
            self.assertEqual(cases[name]['exit'], 1)
            self.assertTrue(cases[name]['stderr_nonempty'])
        self.assertEqual(cases['after-hook']['stdout'], 'hook:after.txt\n')
        tokens = [case['name'] for case in cases.values() if '@PROGRAM@' in case['args']]
        self.assertEqual(tokens, ['strip-default', 'strip-flags'])
        self.assertEqual(cases['strip-flags']['args'], ['-U', '-S', '-S', '@PROGRAM@', 'stripped-flags'])

    def test_metalog_and_directory_cases_match_canonical_limits(self):
        source = self.result[PROGRAM]
        self.assertRegex(source, r'#ifdef SUPPORT_MTREE\n\s*case \'M\':')
        self.assertNotIn('-DSUPPORT_MTREE', self.profile['cppflags'])
        directory = next(case for case in self.profile['runtime_cases'] if case['name'] == 'directory')
        self.assertTrue(all(row['mode'] == 0o755 for row in directory['checks']))
        self.assertIn('mkdir(path, 0777)', source)
        self.assertIn('if (!dounpriv && (', source)


if __name__ == '__main__':
    unittest.main()
