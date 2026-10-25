#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted), not submitted upstream.
"""Check pinned GN source and compiler shell words. Never execute GN or tools."""
import argparse
import ast
import hashlib
from pathlib import Path
import re
import shlex
import sys
import unittest

sys.dont_write_bytecode = True
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, required=True,
                    help='Pinned Chromium tree, before or after this exact patch')
args, remaining = parser.parse_known_args()
PATCH = Path(__file__).resolve().parents[1] / 'patches/gn-mac-gcc16-host.patch'
HASHES = {
    'build/toolchain/mac/BUILD.gn': (
        'dd2d421e1ef8b4b3aa97351ccf7e2b0d77e0e79d51933fc9fd5c46d3dd10d5f7',
        '15e9977abc49f6c7fb6eae9c794ece5a1a53fc72403ac3a076de3442dc138f79'),
    'build/toolchain/apple/toolchain.gni': (
        'e41660cf2c797f8291023ee3956f9e72ffb6ee87d1facdefb8ad0cb2d1e44b05',
        '828b41d6618a70f679d23b141e9d3338d112bb8ba39d5aedd8785f650381cd1e'),
    'build/config/mac/BUILD.gn': (
        '6e6ae8961044eba1668a2e38b47bf15c9e3766d3092b6043b0e7c179df547dbc',
        '38a6f53f5be0ee6054bce07cbded1bc37b2dae6b0f3821251a9b78170d16d65f'),
}


def patch_sources(files, text, reverse=False):
    """Apply only exact complete-file hunks in memory. Refuse offsets and fuzz."""
    lines, result, index = text.splitlines(True), {}, 0
    while index < len(lines):
        if not lines[index].startswith('--- a/'):
            index += 1
            continue
        name = lines[index][6:].strip()
        if lines[index + 1] != '+++ b/' + name + '\n' or name in result:
            raise ValueError('patch target differs or repeats')
        before, output, cursor = files[name].splitlines(True), [], 0
        index += 2
        while index < len(lines) and lines[index].startswith('@@ '):
            match = re.fullmatch(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@[^\n]*\n', lines[index])
            if not match:
                raise ValueError('invalid hunk header')
            starts = (int(match[1]) - 1, int(match[3]) - 1)
            counts = (int(match[2] or 1), int(match[4] or 1))
            old, new = [], []
            index += 1
            while index < len(lines) and lines[index][:1] in (' ', '+', '-') and not lines[index].startswith('--- a/'):
                line = lines[index]
                if line[0] in ' -':
                    old.append(line[1:])
                if line[0] in ' +':
                    new.append(line[1:])
                index += 1
            if (len(old), len(new)) != counts:
                raise ValueError('hunk counts differ')
            start, expected, replacement = (starts[1], new, old) if reverse else (starts[0], old, new)
            if start < cursor or before[start:start + len(expected)] != expected:
                raise ValueError('exact source hunk differs')
            output.extend(before[cursor:start])
            output.extend(replacement)
            cursor = start + len(expected)
        result[name] = ''.join([*output, *before[cursor:]])
    if set(result) != set(HASHES):
        raise ValueError('patch must change exactly the three selected GN files')
    return result


def expression(text, name, operator='='):
    lines = text.splitlines()
    found = []
    for index, line in enumerate(lines):
        match = re.fullmatch(r'\s*' + name + r'\s*' + re.escape(operator) + r'\s*(.*)', line)
        if not match:
            continue
        value = match[1]
        while not value or value.rstrip().endswith('+'):
            index += 1
            value += ' ' + lines[index].strip()
        if 'string_replace(' in value:
            found.append(value)
    if len(found) != 1:
        raise ValueError('select exactly one production quoting expression: ' + name)
    return found[0]


def expand(value, words):
    """Model only string concatenation/replacement in the selected expressions."""
    def visit(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.Name) and node.id in words:
            return words[node.id]
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            return visit(node.left) + visit(node.right)
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and
                node.func.id == 'string_replace' and len(node.args) == 3 and not node.keywords):
            source, old, new = map(visit, node.args)
            return source.replace(old, new)
        raise ValueError('unsupported production string expression')
    return visit(ast.parse('(' + value + ')', mode='eval').body)


def command_words(text, path, arguments, route):
    cc_tail = ''.join(expand(expression(text, 'cc_driver_args', '+='), dict(arg=word)) for word in arguments)
    cxx_tail = ''.join(expand(expression(text, 'cxx_driver_args', '+='), dict(arg=word)) for word in arguments)
    rust_tail = ''.join(expand(expression(text, 'rust_macro_driver_args', '+='), dict(arg=word)) for word in arguments)
    values = dict(_cc=path, _cxx=path, ld=path, cc_driver_args=cc_tail,
                  cxx_driver_args=cxx_tail, rust_macro_driver_args=rust_tail)
    return shlex.split(expand(expression(text, route), values))


CURRENT = {name: (args.source / name).read_text() for name in HASHES}
states = {next((index for index, expected in enumerate(HASHES[name])
                if hashlib.sha256(text.encode()).hexdigest() == expected), -1)
          for name, text in CURRENT.items()}
if states not in ({0}, {1}):
    parser.error('source must contain the complete exact before or after GN files')
BEFORE = CURRENT if states == {0} else patch_sources(CURRENT, PATCH.read_text(), reverse=True)
AFTER = patch_sources(BEFORE, PATCH.read_text())

HOST_ALLOCATOR_ARGS = (
    'use_partition_alloc',
    'use_allocator_shim',
    'use_partition_alloc_as_malloc',
)
HOST_ALLOCATOR_DELTA = """\
      # Host generators use the platform allocator instead of the Apple shim.
      # The independent NetBSD target keeps its allocator policy.
      use_partition_alloc = false
      use_allocator_shim = false
      use_partition_alloc_as_malloc = false
"""
PRIOR_MAC_SHA256 = '7f00e26744199f532db050d023e9fc1b7b7e99f9a8e181ee39187d65e9be32b3'


def source_block(text, heading):
    """Read one brace-delimited source block. Do not evaluate GN."""
    if text.count(heading) != 1:
        raise ValueError('select exactly one source block')
    start = text.index(heading) + len(heading)
    depth = 1
    result = []
    for line in text[start:].splitlines(True):
        syntax = re.sub(r'"(?:\\.|[^"\\])*"|#.*', '', line)
        depth += syntax.count('{') - syntax.count('}')
        if depth == 0:
            return ''.join(result)
        result.append(line)
    raise ValueError('source block did not close')


def host_allocator_modes(mac, apple):
    """Read explicit boolean policy and forwarding. Do not resolve GN defaults."""
    native = source_block(mac, 'template("mac_gcc_toolchain") {')
    forwarded = 'forward_variables_from(invoker.toolchain_args, "*")'
    if forwarded not in native:
        raise ValueError('native family must forward its toolchain arguments')
    selected = {}
    for name in HOST_ALLOCATOR_ARGS:
        values = re.findall(r'^\s*' + name + r' = (true|false)$',
                            native, re.MULTILINE)
        if len(values) != 1:
            raise ValueError('each native allocator argument must be explicit once')
        selected[name] = values[0] == 'true'
    variants = ('', '_for_rust_host_build_tools',
                '_host_with_system_allocator', '_with_system_allocator')
    wrapper = source_block(apple, 'template("apple_toolchain") {')
    for suffix in variants[1:]:
        if '"${target_name}' + suffix + '"' not in wrapper:
            raise ValueError('derived native family must remain present')
    for template in ('apple_rust_host_build_tools_toolchain',
                     'apple_system_allocator_toolchain'):
        derived = source_block(apple, 'template("' + template + '") {')
        if forwarded not in derived:
            raise ValueError('derived family must forward the native arguments')
        for name in HOST_ALLOCATOR_ARGS:
            if re.search(r'^\s*' + name + r'\s*=', derived, re.MULTILINE):
                raise ValueError('derived family must not replace allocator args')
    result = {}
    for family in ('gcc_arm64', 'gcc_arm64_v8_x64'):
        source_block(mac, 'mac_gcc_toolchain("' + family + '") {')
        for suffix in variants:
            result[family + suffix] = dict(selected)
    return result


class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.apple = AFTER['build/toolchain/apple/toolchain.gni']
        self.compiler = "/selected SDK/driver's $literal/g++"
        self.arguments = ['-B/selected driver/', '-specs=/selected/specs with space',
                          '-isysroot', "/selected SDK/it's $literal", '-mmacosx-version-min=26.0']

    def test_complete_three_file_patch_and_inverse(self):
        self.assertEqual(patch_sources(AFTER, PATCH.read_text(), reverse=True), BEFORE)
        for name, text in AFTER.items():
            self.assertEqual(hashlib.sha256(text.encode()).hexdigest(), HASHES[name][1])
        mutant = dict(BEFORE)
        mutant['build/config/mac/BUILD.gn'] = mutant['build/config/mac/BUILD.gn'].replace('common_mac_flags = []', 'common_mac_flags = [ "unexpected" ]')
        with self.assertRaises(ValueError):
            patch_sources(mutant, PATCH.read_text())

    def test_ordered_c_and_cxx_words(self):
        for route in ('cc', 'cxx'):
            self.assertEqual(command_words(self.apple, self.compiler, self.arguments, route),
                             [self.compiler, *self.arguments])

    def test_link_driver_keeps_one_executable_and_separate_tail(self):
        self.assertEqual(command_words(self.apple, self.compiler, self.arguments, 'linker_driver_args'),
                         ['-Wcrl,driver,' + self.compiler, *self.arguments])

    def test_rust_linker_and_arguments_keep_order(self):
        self.assertEqual(command_words(self.apple, self.compiler, self.arguments, 'rust_macro_linker'),
                         ['-Clinker=' + self.compiler, *['-Clink-arg=' + word for word in self.arguments]])

    def test_unquoted_compiler_mutation_is_causal(self):
        original = expression(self.apple, 'cxx')
        mutant = self.apple.replace(original, '_cxx + cxx_driver_args')
        with self.assertRaises((AssertionError, ValueError)):
            self.assertEqual(command_words(mutant, self.compiler, self.arguments, 'cxx'),
                             [self.compiler, *self.arguments])

    def test_dropped_link_argument_mutation_is_causal(self):
        mutant, count = re.subn(r'(string_replace\(ld,[^\n]+) \+ cxx_driver_args', r'\1', self.apple)
        self.assertEqual(count, 1)
        with self.assertRaises(AssertionError):
            self.assertEqual(command_words(mutant, self.compiler, self.arguments, 'linker_driver_args'),
                             ['-Wcrl,driver,' + self.compiler, *self.arguments])

    def test_target_scope_and_native_snapshot_cpu_are_explicit(self):
        mac = AFTER['build/toolchain/mac/BUILD.gn']
        selected = mac.split('template("mac_gcc_toolchain") {', 1)[1]
        for flag in ('use_custom_libcxx = false', 'use_custom_libcxx_for_host = false',
                     'is_clang = false', 'use_reclient = false', 'cc_wrapper = ""'):
            self.assertEqual(selected.count(flag), 1)
        self.assertIn('if (mac_gcc_cc != "") {', selected)
        snapshot = selected.split('mac_gcc_toolchain("gcc_arm64_v8_x64") {', 1)[1]
        self.assertIn('current_cpu = "arm64"', snapshot)
        self.assertIn('v8_current_cpu = "x64"', snapshot)
        self.assertIn('if (is_clang && defined(archs_mapping[current_os]))', AFTER['build/config/mac/BUILD.gn'])
        self.assertNotIn('linux/unbundle', '\n'.join(HASHES))

    def test_host_allocator_delta_preserves_all_prior_mac_source(self):
        mac = AFTER['build/toolchain/mac/BUILD.gn']
        self.assertEqual(mac.count(HOST_ALLOCATOR_DELTA), 1)
        prior = mac.replace(HOST_ALLOCATOR_DELTA, '')
        self.assertEqual(hashlib.sha256(prior.encode()).hexdigest(),
                         PRIOR_MAC_SHA256)
        native = source_block(mac, 'template("mac_gcc_toolchain") {')
        self.assertIn(HOST_ALLOCATOR_DELTA, native)

    def test_both_native_families_and_all_derived_families_use_libc(self):
        modes = host_allocator_modes(AFTER['build/toolchain/mac/BUILD.gn'],
                                     self.apple)
        self.assertEqual(len(modes), 8)
        for family, selected in modes.items():
            self.assertEqual(selected, dict.fromkeys(HOST_ALLOCATOR_ARGS, False),
                             family)

    def test_each_missing_host_allocator_override_is_causal(self):
        mac = AFTER['build/toolchain/mac/BUILD.gn']
        for name in HOST_ALLOCATOR_ARGS:
            with self.subTest(name=name):
                line = '      ' + name + ' = false\n'
                self.assertEqual(mac.count(line), 1)
                mutant = mac.replace(line, '')
                with self.assertRaisesRegex(ValueError, 'must be explicit'):
                    host_allocator_modes(mutant, self.apple)

    def test_derived_argument_forwarding_removal_is_causal(self):
        mac = AFTER['build/toolchain/mac/BUILD.gn']
        heading = 'template("apple_rust_host_build_tools_toolchain") {'
        derived = source_block(self.apple, heading)
        forwarded = 'forward_variables_from(invoker.toolchain_args, "*")'
        self.assertEqual(derived.count(forwarded), 1)
        mutant = self.apple.replace(derived, derived.replace(forwarded, ''))
        with self.assertRaisesRegex(ValueError, 'must forward'):
            host_allocator_modes(mac, mutant)

    def test_existing_native_final_link_commands_remain(self):
        old = BEFORE['build/toolchain/apple/toolchain.gni']
        def command(text, tool):
            block = text.split('tool("' + tool + '") {', 1)[1]
            return next(line for line in block.splitlines() if line.strip().startswith('command = '))
        for tool in ('link', 'solink', 'solink_module', 'rust_bin', 'rust_cdylib', 'rust_dylib'):
            self.assertEqual(command(self.apple, tool), command(old, tool), tool)
        macro = command(old, 'rust_macro').replace('-Clinker=\\"${_cxx}\\"', '$rust_macro_linker')
        self.assertEqual(command(self.apple, 'rust_macro'), macro)


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0], *remaining])
