#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD; AI-assisted finite source-policy controls.
"""Check deferred installer policy as source data. Do not execute BSD make."""
import argparse
import copy
import re
import sys
from pathlib import Path
import types
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT
POLICY = ROOT / 'profiles/development-toolchain/darwin-bootstrap.mk.conf'
MARKER = '# MAKECONF is first read before PKGPATH.'


def apply_policy(text, state):
    """Model only this finite block's assignments and literal predicates."""
    def condition(expression):
        for term in expression.split(' && '):
            match = re.fullmatch(r'(!?)defined\(([^)]+)\)', term)
            if match:
                value = match[2] in state
                if bool(match[1]) == value:
                    return False
                continue
            match = re.fullmatch(r'(!?)empty\(([^:)]+):M\$\{([^}]+)\}\)', term)
            if match:
                member = state[match[3]] in state.get(match[2], '').split()
                if bool(match[1]) != member:
                    return False
                continue
            match = re.fullmatch(r'\$\{([^}:]+)(?::U([^}]+))?\} (==|!=) "([^"]*)"', term)
            if not match:
                raise AssertionError('Unexpected policy predicate: ' + term)
            equal = state.get(match[1], match[2] or '') == match[4]
            if equal != (match[3] == '=='):
                return False
        return True
    stack = []
    for line in text[text.index(MARKER):].splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        directive = re.fullmatch(r'\.\s*(if|elif|endif)\b\s*(.*)', line)
        if directive:
            kind, expression = directive.groups()
            if kind == 'if':
                parent = stack[-1][2] if stack else True
                active = parent and condition(expression)
                stack.append([parent, active, active])
            elif kind == 'elif':
                parent, matched, _ = stack[-1]
                active = parent and not matched and condition(expression)
                stack[-1] = [parent, matched or active, active]
            else:
                stack.pop()
            continue
        if stack and not stack[-1][2]:
            continue
        match = re.fullmatch(r'([A-Za-z0-9_.]+)(\+?=) *(.*)', line)
        if not match:
            raise AssertionError('Unexpected policy statement: ' + line)
        key, op, value = match.groups()
        value = re.sub(r'\$\{([^}]+)\}', lambda found: state[found[1]], value)
        state[key] = ((state.get(key, '') + ' ').lstrip() if op == '+=' else '') + value
    assert not stack
    return state


def seed_make_recipes(policy):
    state = apply_policy(policy, dict(EMBERBSD_DARWIN_BOOTSTRAP='yes', BSD_PKG_MK='1',
                                      PKGPATH='devel/bmake', LOCALBASE='/final/prefix'))
    return state['EMBERBSD_DARWIN_SEED_MAKE_RECIPES'].split()


def dependencies(state):
    return [word.split(':../../', 1)[1] for kind in ('BOOTSTRAP_DEPENDS', 'DEPENDS')
            for word in state.get(kind, '').split()]


def graph(policy):
    result = {'lang/gcc16': ['lang/llvm', 'shells/mksh', 'pkgtools/libnbcompat'],
              'sysutils/bsdinstall': ['pkgtools/libnbcompat'],
              'lang/llvm': ['pkgtools/libnbcompat'], 'shells/mksh': ['pkgtools/libnbcompat'],
              'pkgtools/libnbcompat': []}
    roots = dependencies(apply_policy(policy, dict(EMBERBSD_DARWIN_BOOTSTRAP='yes',
        BSD_PKG_MK='1', PKGPATH='lang/gcc16', LOCALBASE='/final/prefix',
        _EMBERBSD_DARWIN_INITIAL_GMAKE='/initial/gmake SHELL=/initial/sh')))
    for name in roots:
        result.setdefault(name, [])
    for name in result:
        result[name] += dependencies(apply_policy(policy, dict(EMBERBSD_DARWIN_BOOTSTRAP='yes',
            BSD_PKG_MK='1', PKGPATH=name, LOCALBASE='/final/prefix',
            _EMBERBSD_DARWIN_INITIAL_GMAKE='/initial/gmake SHELL=/initial/sh')))
    return result


def reachable(graph):
    visited = set()
    def visit(name, active):
        if name in active:
            raise ValueError('dependency cycle')
        if name not in visited:
            for target in graph[name]:
                visit(target, active | {name})
            visited.add(name)
    visit('lang/gcc16', set())
    return visited


class InstallerPolicyTests(unittest.TestCase):
    def setUp(self):
        self.text = POLICY.read_text()
        self.state = dict(EMBERBSD_DARWIN_BOOTSTRAP='yes', BSD_PKG_MK='1',
                          LOCALBASE='/final/prefix', EMBERBSD_DARWIN_SH='/initial/sh',
                          _EMBERBSD_DARWIN_INITIAL_GMAKE='/initial/gmake SHELL=/initial/sh',
                          EMBERBSD_GCC16_STRIP='/initial/strip')

    def test_early_read_defers_and_late_read_applies_once(self):
        state = copy.deepcopy(self.state)
        self.assertEqual(apply_policy(self.text, state), self.state)
        state['PKGPATH'] = 'lang/gcc16'
        apply_policy(self.text, state)
        self.assertIn('sysutils/bsdinstall', dependencies(state))
        previous = dict(state)
        self.assertEqual(apply_policy(self.text, state), previous)
        depth = 0
        for line in self.text[:self.text.index(MARKER)].splitlines():
            keyword = line.lstrip()[1:].lstrip().split(None, 1)[0] if line.lstrip().startswith('.') else ''
            if keyword in ('if', 'ifdef', 'ifndef'):
                depth += 1
            elif keyword == 'endif':
                depth -= 1
        self.assertEqual(depth, 0, 'The deferred block is inside the early one-time guard')

    def test_ordinary_and_unrelated_contexts_are_unchanged(self):
        state = dict(self.state, EMBERBSD_DARWIN_BOOTSTRAP='no', PKGPATH='lang/gcc16')
        before = dict(state)
        self.assertEqual(apply_policy(self.text, state), before)
        for name in ('lang/python315', 'pkgtools/libnbcompat'):
            state = apply_policy(self.text, dict(self.state, PKGPATH=name))
            self.assertNotIn('sysutils/bsdinstall', dependencies(state))
            self.assertNotIn('EMBERBSD_BSDINSTALL_SHELL', state)
        state = dict(self.state, PKGPATH='lang/gcc16')
        del state['BSD_PKG_MK']
        self.assertEqual(apply_policy(self.text, dict(state)), state)

    def test_provider_children_use_final_bundle_paths(self):
        state = apply_policy(self.text, dict(self.state, PKGPATH='sysutils/bsdinstall'))
        self.assertEqual(set(dependencies(state)), {'shells/mksh', 'lang/llvm', 'devel/bmake'})
        self.assertEqual(len(state['DEPENDS'].split()), 2)
        self.assertEqual(state['BOOTSTRAP_DEPENDS'].split(':../../')[1], 'devel/bmake')
        self.assertEqual(state['EMBERBSD_BSDINSTALL_SHELL'], '/final/prefix/bin/mksh')
        self.assertEqual(state['TOOLS_PLATFORM.strip'], '/final/prefix/bin/llvm-strip')
        for original, seed in (('${LOCALBASE}/bin/mksh', '${EMBERBSD_DARWIN_SH}'),
                               ('${LOCALBASE}/bin/llvm-strip', '${EMBERBSD_GCC16_STRIP}')):
            mutant = self.text.replace(original, seed)
            value = apply_policy(mutant, dict(self.state, PKGPATH='sysutils/bsdinstall'))
            self.assertTrue(any(value[key].startswith('/initial/') for key in
                ('EMBERBSD_BSDINSTALL_SHELL', 'TOOLS_PLATFORM.strip')))

    def test_profile_edges_are_acyclic_and_global_edge_would_fail(self):
        value = graph(self.text)
        self.assertEqual(reachable(value), set(value))
        self.assertNotIn('sysutils/bsdinstall', value['pkgtools/libnbcompat'])
        mutant = self.text.replace('.    if ${PKGPATH} == "lang/gcc16"',
                                   '.    if ${PKGPATH} != ""')
        with self.assertRaisesRegex(ValueError, 'dependency cycle'):
            reachable(graph(mutant))

    def test_dependency_floor_and_payloads_match_canonical_sources(self):
        package = (SOURCE / 'upstream/pkgsrc/sysutils/bsdinstall/Makefile').read_text()
        version = re.search(r'^DISTNAME=\s*bsdinstall-(\S+)', package, re.M)[1]
        revision = re.search(r'^PKGREVISION=\s*(\S+)', package, re.M)[1]
        state = apply_policy(self.text, dict(self.state, PKGPATH='lang/gcc16'))
        self.assertEqual(state['BOOTSTRAP_DEPENDS'].split(':', 1)[0], 'bsdinstall>=' + version + 'nb' + revision)
        self.assertIn('bin/bsdinstall\n', (SOURCE / 'upstream/pkgsrc/sysutils/bsdinstall/PLIST').read_text())
        self.assertIn('bin/mksh\n', (SOURCE / 'upstream/pkgsrc/shells/mksh/PLIST').read_text())
        self.assertIn('bin/llvm-strip\n', (SOURCE / 'pkgsrc/lang/llvm/PLIST').read_text())

    def test_shell_opt_in_is_checked_after_package_preferences(self):
        path = ROOT / 'profiles/common-build-tools/tests/bsdinstall-source.py'
        module = types.ModuleType('bsd_source_control')
        module.__file__ = str(path)
        exec(compile(path.read_bytes(), str(path), 'exec'), module.__dict__)
        originals = {name: (SOURCE / 'upstream/pkgsrc' / name).read_text()
                     for name in (module.RECIPE, module.PROGRAM)}
        new = module.replay(originals, module.PATCH.read_text())[module.RECIPE]
        old_patch = SOURCE / 'profiles/common-build-tools/patches/pkgsrc-bsdinstall-native-shell.patch'
        old = module.replay(originals, old_patch.read_text())[module.RECIPE]
        include = '.include "../../mk/bsd.prefs.mk"'
        guard = '.if defined(EMBERBSD_BSDINSTALL_SHELL)'
        self.assertLess(new.index(include), new.index(guard))
        # This source check compares the former early placement with the repaired order.
        if old != new:
            self.assertLess(old.index(guard), old.index(include))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ports-source', type=Path, default=ROOT,
                        help='explicit original Ports checkout for unchanged source data')
    args, remaining = parser.parse_known_args()
    SOURCE = args.ports_source
    unittest.main(argv=[__file__, *remaining])
