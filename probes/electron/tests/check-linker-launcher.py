#!/usr/bin/env python3
# Copyright (c) 2026 The EmberBSD project contributors.
# SPDX-License-Identifier: BSD-2-Clause
# AI-assisted implementation for EmberBSD Ports.
"""Check captured GN Ninja rules without running build commands."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import unittest

CPP_LINKS = {'link', 'solink', 'solink_module'}
RUST_LINKS = {'rust_bin', 'rust_cdylib', 'rust_dylib', 'rust_macro'}
NATIVE_LINKS = CPP_LINKS | RUST_LINKS


def logical_lines(text):
    """Join Ninja dollar-newline continuations without expanding variables."""
    result, pending = [], ''
    for line in text.splitlines(keepends=True):
        if pending:
            line = line.lstrip(' \t')
        content = line.removesuffix('\n').removesuffix('\r')
        trailing = len(content) - len(content.rstrip('$'))
        if line.endswith('\n') and trailing % 2:
            pending += content[:-1]
        else:
            result.append(pending + line)
            pending = ''
    if pending:
        result.append(pending)
    return result


def tool_type(rule):
    for name in sorted(NATIVE_LINKS, key=len, reverse=True):
        if rule == name or rule.endswith('_' + name):
            return name
    return None


def prefixed_command(command, kind, launcher):
    # Apple TOOL_VERSION is a shell assignment, not a launcher executable.
    env = re.match(r'TOOL_VERSION=[^ ]+ ', command)
    if env:
        return command[:env.end()] + launcher + ' ' + command[env.end():]
    # A Rust native-output invocation includes code generation and final link.
    if kind in RUST_LINKS:
        return launcher + ' ' + command
    # The GCC link/solink Python drivers pass the real linker after "--".
    if ' -- ' in command:
        return command.replace(' -- ', ' -- ' + launcher + ' ', 1)
    return launcher + ' ' + command


def check_rules(before, after, launcher, wrapped):
    if not wrapped:
        if before != after:
            raise ValueError('An unselected toolchain changed')
        return []
    expected, found, rule = [], [], None
    for line in logical_lines(before):
        if line.startswith('rule '):
            rule = line.split()[1]
        elif line.strip() and not line[0].isspace():
            rule = None
        if line.startswith('  command = ') and rule is not None:
            kind = tool_type(rule)
            if kind:
                command = line[len('  command = '):].removesuffix('\n')
                if launcher in command:
                    raise ValueError('The before command already contains the launcher')
                ending = '\n' if line.endswith('\n') else ''
                line = '  command = ' + prefixed_command(command, kind, launcher) + ending
                found.append(kind)
        expected.append(line)
    if not CPP_LINKS.issubset(found):
        raise ValueError('A selected toolchain lacks a C/C++ final-link rule')
    rust = set(found) & RUST_LINKS
    if rust and rust != RUST_LINKS:
        raise ValueError('A selected toolchain has an incomplete Rust rule family')
    if len(found) != len(set(found)):
        raise ValueError('Duplicate final-link rule types')
    if ''.join(expected) != ''.join(logical_lines(after)):
        raise ValueError('Commands or rule data differ beyond the selected link prefixes')
    return sorted(found)


def check_pool(text, name):
    pool, depths, definitions = None, [], 0
    for line in logical_lines(text):
        if line.startswith('pool '):
            pool = line.split()[1]
            if pool == name:
                definitions += 1
        elif line.strip() and not line[0].isspace():
            pool = None
        if pool == name and re.match(r'\s+depth\s*=', line):
            depths.append(line.split('=', 1)[1].strip())
    if definitions != 1 or depths != ['1']:
        raise ValueError('The selected after link pool must have one depth=1 definition')


def check_graph(before, after, wrapped, launcher, pool_name):
    if not launcher or any(char in launcher for char in '\r\n'):
        raise ValueError('Use one nonempty command prefix without newlines')
    old = {str(path.relative_to(before)): path for path in before.rglob('toolchain.ninja')}
    new = {str(path.relative_to(after)): path for path in after.rglob('toolchain.ninja')}
    if not old or old.keys() != new.keys():
        raise ValueError('The captured toolchain file sets differ or are empty')
    if not wrapped or not wrapped.issubset(old):
        raise ValueError('Select existing relative toolchain.ninja paths to wrap')
    rows = []
    for name in sorted(old):
        first, second = old[name].read_bytes(), new[name].read_bytes()
        try:
            kinds = check_rules(first.decode(), second.decode(), launcher, name in wrapped)
        except ValueError as error:
            raise ValueError(name + ': ' + str(error)) from error
        rows.append({'path': name, 'wrapped_rule_types': kinds,
                     'before_sha256': hashlib.sha256(first).hexdigest(),
                     'after_sha256': hashlib.sha256(second).hexdigest()})
    pool_file = after / 'build.ninja'
    check_pool(pool_file.read_text(), pool_name)
    return {'status': 'PASS', 'toolchains': rows, 'link_pool': pool_name,
            'link_pool_depth': 1, 'after_build_ninja_sha256': hashlib.sha256(pool_file.read_bytes()).hexdigest(),
            'scope': 'Captured Ninja rule comparison only; no compiler, launcher, or linker execution'}


class InvariantTests(unittest.TestCase):
    def setUp(self):
        self.launcher = '/host/python3 /host/SDK/scripts/link-launcher.py --lock-root /obj --context /obj/heavy --'
        self.before = 'rule cxx\n  command = cxx -c source.cc\nrule alink\n  command = ar rcs lib.a\n'
        self.before += 'rule rust_rlib\n  command = rustc --crate-type=rlib\nrule rust_staticlib\n  command = rustc --crate-type=staticlib\n'
        for kind in sorted(NATIVE_LINKS):
            command = 'rust-wrapper' if kind in RUST_LINKS else 'python gcc-wrapper -- cxx @input.rsp'
            self.before += 'rule ' + kind + '\n  command = ' + command + '\n'
        self.after = self.before
        for kind in sorted(NATIVE_LINKS):
            old = '  command = ' + ('rust-wrapper' if kind in RUST_LINKS else 'python gcc-wrapper -- cxx @input.rsp')
            new = '  command = ' + prefixed_command(old[len('  command = '):], kind, self.launcher)
            self.after = self.after.replace('rule ' + kind + '\n' + old, 'rule ' + kind + '\n' + new)

    def test_exact_changes(self):
        self.assertEqual(check_rules(self.before, self.after, self.launcher, True), sorted(NATIVE_LINKS))

    def test_compiler_mutation_is_rejected(self):
        with self.assertRaises(ValueError):
            check_rules(self.before, self.after.replace('cxx -c source.cc', 'cxx -DCHANGED -c source.cc'), self.launcher, True)

    def test_rust_bypass_is_rejected(self):
        with self.assertRaises(ValueError):
            check_rules(self.before, self.after.replace(self.launcher + ' rust-wrapper', 'rust-wrapper', 1), self.launcher, True)

    def test_apple_env_order_is_rejected(self):
        old = self.before.replace('python gcc-wrapper -- cxx @input.rsp', 'TOOL_VERSION=17 linker-driver @input.rsp')
        new = self.after.replace('python gcc-wrapper -- ' + self.launcher + ' cxx @input.rsp', self.launcher + ' TOOL_VERSION=17 linker-driver @input.rsp')
        with self.assertRaises(ValueError):
            check_rules(old, new, self.launcher, True)

    def test_unselected_toolchain_change_is_rejected(self):
        with self.assertRaises(ValueError):
            check_rules(self.before, self.after, self.launcher, False)

    def test_pool_depth(self):
        check_pool('pool build_toolchain_link_pool\n  depth = 1\n', 'build_toolchain_link_pool')
        with self.assertRaises(ValueError):
            check_pool('pool build_toolchain_link_pool\n  depth = 2\n', 'build_toolchain_link_pool')
        with self.assertRaises(ValueError):
            check_pool('pool build_toolchain_link_pool\n  depth = 2\npool build_toolchain_link_pool\n  depth = 1\n', 'build_toolchain_link_pool')

    def test_ninja_continuations(self):
        self.assertEqual(logical_lines('command = first$\n  second\n'), ['command = firstsecond\n'])
        self.assertEqual(logical_lines('command = literal$$\nnext\n'), ['command = literal$$\n', 'next\n'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before', type=Path, help='Directory with captured before Ninja files')
    parser.add_argument('--after', type=Path, help='Directory with captured after Ninja files')
    parser.add_argument('--wrap', action='append', default=[], help='Relative toolchain.ninja path expected to gain the prefix; repeat for each family')
    parser.add_argument('--launcher', help='Exact prefix as written in the generated Ninja commands')
    parser.add_argument('--link-pool', default='build_toolchain_link_pool')
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(InvariantTests)
        return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1
    if args.before is None or args.after is None or args.launcher is None:
        parser.error('--before, --after and --launcher are required')
    try:
        result = check_graph(args.before, args.after, set(args.wrap), args.launcher, args.link_pool)
    except (ValueError, OSError, UnicodeError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
