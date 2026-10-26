#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Check the pinned GN source changes without running a compiler or GN."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import sys
import tarfile
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[3]
RECIPE = ROOT / 'pkgsrc/devel/gn'
ARCHIVE = None
ORIGINAL = None
PATCHED = None


def apply_exact(source, patch):
    before = source.splitlines(keepends=True)
    lines = patch.splitlines(keepends=True)
    out, cursor, index = [], 0, 0
    while index < len(lines):
        match = re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', lines[index])
        if not match:
            index += 1
            continue
        start = int(match[1]) - 1
        assert start >= cursor
        out.extend(before[cursor:start])
        cursor = start
        removed = added = 0
        index += 1
        while index < len(lines) and lines[index][:1] in (' ', '+', '-'):
            row = lines[index]
            if row[0] in ' -':
                assert cursor < len(before) and before[cursor] == row[1:]
                cursor += 1
                removed += 1
            if row[0] in ' +':
                out.append(row[1:])
                added += 1
            index += 1
        assert removed == int(match[2] or 1)
        assert added == int(match[4] or 1)
    out.extend(before[cursor:])
    return ''.join(out)


def function(name, source= None, **bindings):
    tree = ast.parse(PATCHED if source is None else source)
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    scope = dict(re=re, shlex=shlex, REPO_ROOT='/source', **bindings)
    exec(compile(ast.Module(body=[node], type_ignores=[]), '<GN source function>', 'exec'), scope)
    return scope[name]


def probe(source=None, platform='posix', status=0, output='#define __GNUC__ 16\n'):
    calls = []
    def run(*args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(returncode=status, stdout=output)
    selected = function('is_gcc', source, os=SimpleNamespace(name=platform),
                        subprocess=SimpleNamespace(run=run, DEVNULL=-3))
    return selected, calls


class GNRecipeTests(unittest.TestCase):
    def test_complete_archive_checksum_and_patch_pin(self):
        raw = ARCHIVE.read_bytes()
        info = (RECIPE / 'distinfo').read_text()
        for name, digest in [('BLAKE2s', hashlib.blake2s(raw).hexdigest()),
                             ('SHA512', hashlib.sha512(raw).hexdigest())]:
            self.assertIn(f'{name} ({ARCHIVE.name}) = {digest}', info)
        self.assertIn(f'Size ({ARCHIVE.name}) = {len(raw)} bytes', info)
        patch = (RECIPE / 'patches/patch-build_gen.py').read_bytes()
        filtered = b''.join(row + b'\n' for row in patch.splitlines() if b'$NetBSD' not in row)
        self.assertIn('SHA1 (patch-build_gen.py) = ' + hashlib.sha1(filtered).hexdigest(), info)

    def test_posix_probe_preserves_words_without_system_shell(self):
        words = ["/selected SDK/compiler's $literal/g++", '-B/selected prefix/', '-DVALUE=space value;exit 99']
        selected, calls = probe()
        self.assertTrue(selected(shlex.join(words)))
        self.assertEqual(calls[0][0], (words + ['-dM', '-E', '-'],))
        self.assertIs(calls[0][1]['shell'], False)
        self.assertEqual(calls[0][1]['stdin'], -3)
        old, baseline = probe(ORIGINAL)
        old(shlex.join(words))
        self.assertIs(baseline[0][1]['shell'], True)
        self.assertNotEqual(baseline[0][0], calls[0][0])

    def test_windows_and_macro_guards_are_unchanged(self):
        words = '"C:\\GCC tools\\g++.exe" -Bprefix/'
        selected, calls = probe(platform='nt')
        self.assertTrue(selected(words))
        self.assertEqual(calls[0][0], (words + ' -dM -E -',))
        self.assertIs(calls[0][1]['shell'], True)
        for status, text, expected in [(0, '#define __GNUC__ 16\n', True),
                (0, '#define __GNUC__ 4\n#define __clang__ 1\n', False),
                (1, '#define __GNUC__ 16\n', False), (0, '', False)]:
            with self.subTest(status=status, text=text):
                selected, _ = probe(status=status, output=text)
                self.assertIs(selected('/selected/g++'), expected)

    def test_archive_version_keeps_exact_commit_identity_without_git(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'last_commit_position.h'
            env = SimpleNamespace(environ={'GN_VERSION': '2486 (641ace93dd95)'}, path=os.path)
            selected = function('GenerateLastCommitPosition', os=env,
                                subprocess=SimpleNamespace(check_output=lambda *a, **k: self.fail('unexpected git')))
            selected(SimpleNamespace(is_windows=lambda: False), str(target))
            text = target.read_text()
            self.assertIn('#define LAST_COMMIT_POSITION_NUM 2486', text)
            self.assertIn('#define LAST_COMMIT_POSITION "2486 (641ace93dd95)"', text)
            before = target.stat().st_mtime_ns
            selected(SimpleNamespace(is_windows=lambda: False), str(target))
            self.assertEqual(target.stat().st_mtime_ns, before)

    def test_archive_version_rejects_malformed_identity(self):
        for value in ['', '2486', '2486 (UNKNOWN)', '2486 (641ace93dd95)\n', '1;exit 99 (641ace93dd95)']:
            with self.subTest(value=value):
                selected = function('GenerateLastCommitPosition',
                    os=SimpleNamespace(environ={'GN_VERSION': value}, path=os.path))
                with self.assertRaises(ValueError):
                    selected(SimpleNamespace(is_windows=lambda: False), '/unused-output')

    def test_darwin_explicit_sdk_deployment_flags_are_not_replaced(self):
        def apply_flags(source, compile_flags, link_flags):
            tree = ast.parse(source)
            candidates = [node for node in ast.walk(tree) if isinstance(node, ast.If)
                          and any(isinstance(item, ast.Assign) and
                                  any(isinstance(target, ast.Name) and
                                      target.id == 'min_mac_version_flag'
                                      for target in item.targets)
                                  for item in node.body)]
            self.assertEqual(len(candidates), 1)
            scope = dict(cflags=list(compile_flags), ldflags=list(link_flags))
            exec(compile(ast.Module(body=candidates[0].body, type_ignores=[]),
                         '<GN Darwin deployment flags>', 'exec'), scope)
            return scope['cflags'], scope['ldflags']
        provided = ['-O2', '-mmacosx-version-min=26.0']
        self.assertEqual(apply_flags(PATCHED, provided, provided), (provided, provided))
        baseline = apply_flags(ORIGINAL, provided, provided)
        self.assertEqual(baseline[0][-1], '-mmacosx-version-min=14')
        self.assertNotEqual(baseline, (provided, provided))
        self.assertEqual(apply_flags(PATCHED, [], []),
                         (['-mmacosx-version-min=14'], ['-mmacosx-version-min=14']))
        self.assertEqual(apply_flags(PATCHED, provided, []),
                         (provided, ['-mmacosx-version-min=14']))

    def test_gn_environment_follows_pkgsrc_generic_bindings(self):
        recipe = (RECIPE / 'Makefile').read_text()
        self.assertIn('${SETENV} ${CONFIGURE_ENV} ${GN_ENV} ${TOOL_PYTHONBIN}', recipe)
        self.assertEqual(recipe.count('${SETENV} ${MAKE_ENV} ${GN_ENV}'), 2)
        self.assertIn('CFLAGS= CXXFLAGS=${GN_CXXFLAGS:Q}', recipe)
        self.assertIn('GN_CXXFLAGS=\t\t${CPPFLAGS} ${CXXFLAGS}', recipe)
        self.assertNotIn('MAKE_ENV+=\t\t${CONFIGURE_ENV}', recipe)

    def test_recipe_keeps_cross_tools_and_diagnostics_separate(self):
        recipe = (RECIPE / 'Makefile').read_text()
        for exact in ['GCC_REQD+=\t\t16.2', 'ONLY_FOR_COMPILER=\tgcc',
                'PYTHON_FOR_BUILD_ONLY=\ttool', '--platform ${LOWER_OPSYS:Q}',
                '--host ${NATIVE_LOWER_OPSYS:Q}', '${TOOLBASE}/bin/ninja',
                '-j ${_MAKE_JOBS_N} gn\n', '-j ${_MAKE_JOBS_N} gn_unittests\n']:
            self.assertIn(exact, recipe)
        self.assertNotIn('--allow-warnings', recipe)
        self.assertNotIn('--use-lto', recipe)
        self.assertNotIn('buildtools/mac/gn', recipe)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True, type=Path)
    args, remaining = parser.parse_known_args()
    ARCHIVE = args.archive
    with tarfile.open(ARCHIVE, 'r:*') as archive:
        candidates = [m for m in archive.getmembers() if m.name == 'build/gen.py']
        if len(candidates) != 1 or not candidates[0].isfile():
            raise SystemExit('The pinned archive must contain one regular build/gen.py.')
        ORIGINAL = archive.extractfile(candidates[0]).read().decode()
    PATCHED = apply_exact(ORIGINAL, (RECIPE / 'patches/patch-build_gen.py').read_text())
    unittest.main(argv=[sys.argv[0], *remaining])
