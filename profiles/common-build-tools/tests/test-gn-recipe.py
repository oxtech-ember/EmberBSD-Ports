#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Check the pinned GN source changes without running a compiler or GN."""
import argparse
import ast
import hashlib
import importlib.util
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
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
RECIPE = ROOT / 'pkgsrc/devel/gn'
ARCHIVE = None
ORIGINAL = None
PATCHED = None
NINJA_SOURCE = None
TEMPLATES = {}
BUILD_MODULES = {}
INITIAL_CXX = None


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
    def test_actual_generator_preserves_selected_clang_and_gcc_routes(self):
        cases = [('darwin', 'clang', None), ('netbsd', 'clang', None), ('darwin', 'gcc', None)]
        if INITIAL_CXX:
            cases.append(('darwin', 'clang', INITIAL_CXX))
        for target, family, initial in cases:
            with self.subTest(target=target, family=family, actual=bool(initial)), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / 'build').mkdir()
                (root / 'build/gen.py').write_text(PATCHED)
                (root / 'build/ninja_file.py').write_text(NINJA_SOURCE)
                for name, data in {**TEMPLATES, **BUILD_MODULES}.items():
                    (root / 'build' / name).write_bytes(data)
                gen_spec = importlib.util.spec_from_file_location('gn_recipe_generator', root / 'build/gen.py')
                ninja_spec = importlib.util.spec_from_file_location('ninja_file', root / 'build/ninja_file.py')
                generator = importlib.util.module_from_spec(gen_spec)
                ninja = importlib.util.module_from_spec(ninja_spec)
                cxx = initial or '/selected/' + target + '/' + ('clang++' if family == 'clang' else 'g++')
                ar = '/selected/' + target + '/ar'
                include = root / 'selected/include'
                (include / 'rust').mkdir(parents=True)
                (include / 'rust/cxx.h').write_text('// selected header\n')
                env = dict(CXX=cxx, AR=ar, GN_CXX_INCLUDE=str(include), GN_VERSION='2610 (84f10d13f904)',
                           CXXFLAGS='-DSELECTED_INPUT=1 -mmacosx-version-min=26.0',
                           LDFLAGS='-mmacosx-version-min=26.0')
                macros = '#define __GNUC__ 4\n#define __clang__ 1\n' if family == 'clang' else '#define __GNUC__ 16\n'
                with mock.patch.dict(sys.modules, {'ninja_file': ninja, generator.__name__: generator}), \
                        mock.patch.object(sys, 'path', [str(root / 'build'), *sys.path]):
                    ninja_spec.loader.exec_module(ninja)
                    gen_spec.loader.exec_module(generator)
                    real_run = generator.subprocess.run

                    def macro_probe(*args, **kwargs):
                        self.assertEqual(args, (shlex.split(cxx) + ['-dM', '-E', '-'],))
                        self.assertFalse(kwargs['shell'])
                        if not initial:
                            return SimpleNamespace(returncode=0, stdout=macros)
                        result = real_run(*args, **kwargs, timeout=30)
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertIn('#define __clang__ 1', result.stdout)
                        return result

                    with mock.patch.dict(os.environ, env, clear=True), \
                            mock.patch.object(generator.subprocess, 'run', side_effect=macro_probe) as probe_call, \
                            mock.patch.object(generator.subprocess, 'check_output', side_effect=AssertionError('unexpected Git invocation')):
                        self.assertEqual(generator.main(['--platform', target, '--host', 'darwin',
                                                         '--out-path', str(root / 'out')]), 0)
                        self.assertEqual(probe_call.call_count, 1)
                        self.assertEqual(probe_call.call_args.args, (shlex.split(cxx) + ['-dM', '-E', '-'],))
                        self.assertFalse(probe_call.call_args.kwargs['shell'])
                        if target == 'darwin' and family == 'clang' and not initial:
                            self.assertEqual(generator.main(['--platform', target, '--host', 'darwin',
                                                             '--starlark', '--out-path', str(root / 'out-starlark')]), 0)
                            starlark = (root / 'out-starlark/build.ninja').read_text()
                            self.assertIn('cargo_flags = --offline --locked --lib', starlark)
                            self.assertIn('cargo_flags = --workspace --offline --locked --tests', starlark)
                text = (root / 'out/build.ninja').read_text()
                self.assertIn('cxx = ' + cxx + '\n', text)
                self.assertIn(str(include), text)
                self.assertNotIn('starlark/vendor/cxx/include', text)
                self.assertIn('ld = ' + cxx + '\n', text)
                self.assertIn('ar = ' + ar + '\n', text)
                self.assertIn('-std=c++23', text)
                self.assertIn('-Werror', text)
                self.assertIn('-DSELECTED_INPUT=1', text)
                self.assertNotIn('-flto', text)
                self.assertEqual('-Wrange-loop-analysis' in text, family == 'clang')
                self.assertEqual('-Wno-restrict' in text, family == 'gcc')
                self.assertNotIn('-mmacosx-version-min=14', text)

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
            env = SimpleNamespace(environ={'GN_VERSION': '2610 (84f10d13f904)'}, path=os.path)
            selected = function('GenerateLastCommitPosition', os=env,
                                subprocess=SimpleNamespace(check_output=lambda *a, **k: self.fail('unexpected git')))
            selected(SimpleNamespace(is_windows=lambda: False), str(target), False)
            text = target.read_text()
            self.assertIn('#define LAST_COMMIT_POSITION_NUM 2610', text)
            self.assertIn('#define LAST_COMMIT_POSITION "2610 (84f10d13f904)"', text)
            before = target.stat().st_mtime_ns
            selected(SimpleNamespace(is_windows=lambda: False), str(target), False)
            self.assertEqual(target.stat().st_mtime_ns, before)

    def test_dummy_version_overrides_selected_archive_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'last_commit_position.h'
            env = SimpleNamespace(environ={'GN_VERSION': '2610 (84f10d13f904)'}, path=os.path)
            selected = function('GenerateLastCommitPosition', os=env)
            selected(SimpleNamespace(is_windows=lambda: False), str(target), True)
            self.assertIn('#define LAST_COMMIT_POSITION "0 (UNKNOWN)"', target.read_text())

    def test_archive_version_rejects_malformed_identity(self):
        for value in ['', '2610', '2610 (UNKNOWN)', '2610 (84f10d13f904)\n', '1;exit 99 (84f10d13f904)']:
            with self.subTest(value=value):
                selected = function('GenerateLastCommitPosition',
                    os=SimpleNamespace(environ={'GN_VERSION': value}, path=os.path))
                with self.assertRaises(ValueError):
                    selected(SimpleNamespace(is_windows=lambda: False), '/unused-output', False)

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

    def test_generator_refuses_missing_selected_tools(self):
        for env in ({}, {'CXX': '/selected/clang++'}, {'AR': '/selected/llvm-ar'}):
            with self.subTest(env=env):
                selected = function('WriteGNNinja', os=SimpleNamespace(environ=env))
                with self.assertRaisesRegex(ValueError, 'select explicit CXX and AR'):
                    selected('/unused', None, None, None, None)
        self.assertNotIn('install(toolchain.packages)', PATCHED)

    def test_recipe_keeps_cross_tools_and_diagnostics_separate(self):
        recipe = (RECIPE / 'Makefile').read_text()
        for exact in ['USE_CXX_FEATURES=\tc++23', 'ONLY_FOR_COMPILER=\tclang gcc',
                'PYTHON_FOR_BUILD_ONLY=\ttool', '--platform ${LOWER_OPSYS:Q}',
                '--host ${NATIVE_LOWER_OPSYS:Q}', '${TOOLBASE}/bin/ninja',
                '-j ${_MAKE_JOBS_N} gn\n', '-j ${_MAKE_JOBS_N} gn_unittests\n']:
            self.assertIn(exact, recipe)
        self.assertNotIn('GCC_REQD', recipe)
        self.assertNotIn('--allow-warnings', recipe)
        self.assertNotIn('--use-lto', recipe)
        self.assertNotIn('buildtools/mac/gn', recipe)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True, type=Path)
    parser.add_argument('--initial-cxx-command', help='explicit initial Clang command for macro inspection only')
    args, remaining = parser.parse_known_args()
    ARCHIVE = args.archive
    INITIAL_CXX = args.initial_cxx_command
    if INITIAL_CXX and not Path(shlex.split(INITIAL_CXX)[0]).is_absolute():
        parser.error('--initial-cxx-command must name an absolute compiler')
    with tarfile.open(ARCHIVE, 'r:*') as archive:
        candidates = [m for m in archive.getmembers() if m.name == 'build/gen.py']
        if len(candidates) != 1 or not candidates[0].isfile():
            raise SystemExit('The pinned archive must contain one regular build/gen.py.')
        ORIGINAL = archive.extractfile(candidates[0]).read().decode()
        NINJA_SOURCE = archive.extractfile('build/ninja_file.py').read().decode()
        BUILD_MODULES = {name: archive.extractfile('build/' + name).read() for name in ('pinned.py', 'target.py')}
        TEMPLATES = {Path(m.name).name: archive.extractfile(m).read() for m in archive.getmembers()
                     if m.isfile() and m.name.startswith('build/') and m.name.endswith('.template')}
    PATCHED = apply_exact(ORIGINAL, (RECIPE / 'patches/patch-build_gen.py').read_text())
    unittest.main(argv=[sys.argv[0], *remaining])
