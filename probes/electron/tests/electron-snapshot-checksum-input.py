#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted), not submitted upstream.
"""Check the selected snapshot checksum GN source. Do not execute GN or tools."""
import argparse
import ast
import hashlib
from pathlib import Path
import re
import sys
import unittest

sys.dont_write_bytecode = True
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, required=True, help='Pinned Electron source before or after this patch')
args, remaining = parser.parse_known_args()
PATCH = Path(__file__).resolve().parents[1] / 'patches/electron-snapshot-checksum-input.patch'
HASHES = {'BUILD.gn': ('48e0d00e1e51bde7c5937b254bbe1c51585cac4a43734d5cb65fbb07fec4639c',
                       'b32f3297c5f96b6ea300ccc63cea3fd2df4cbeef844c8cc1574f39a4bd3cef98')}
UNCHANGED = {'build/checksum_header.py': 'c7fef509cc8278fae6b7ffb8d046a37991e3a90db5381091187289c8f3b3f363', 'shell/app/electron_main_delegate.cc': '0455b6bf9bfc46bd8b62e1598d03a55e2c971f3cc14152f61bd74c1cad7c53ab', 'shell/browser/javascript_environment.cc': '79a0d06430197e24c842feb83d4f041cc510a7973d23fb2c138523bfb98e6d28'}


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
        raise ValueError('patch must change only the selected Electron BUILD.gn')
    return result


def block(text, heading):
    start = text.index(heading) + len(heading)
    depth, lines = 1, []
    for line in text[start:].splitlines(True):
        syntax = re.sub(r'"(?:\\.|[^"\\])*"|#.*', '', line)
        for char in syntax:
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    return ''.join(lines)
        lines.append(line)
    raise ValueError('source block did not close')


def checksum_route(text, external, default, context):
    """Inspect only the fixed guard and literal input/dependency branches."""
    matches = re.findall(r'if \(([^{}]+)\) \{\s*deps \+= \[ ":mksnapshot_checksum_gen" \]\s*}', text)
    if len(matches) != 1:
        raise ValueError('select exactly one checksum dependency guard')
    values = {'v8_use_external_startup_data': external,
              'current_toolchain == default_toolchain': default,
              'use_v8_context_snapshot': context}
    terms = [term.strip() for term in matches[0].split('&&')]
    if len(terms) != len(set(terms)) or any(term not in values for term in terms):
        raise ValueError('unsupported checksum dependency guard')
    if not all(values[term] for term in terms):
        return None
    action = block(text, 'action("mksnapshot_checksum_gen") {')
    if 'if (use_v8_context_snapshot) {' in action:
        selected = block(action, 'if (use_v8_context_snapshot) {') if context else block(action, 'else {')
    else:
        selected = action
    result = []
    for name in ('inputs', 'deps'):
        matches = re.findall(r'^\s*' + name + r' = (\[[^\n]+\])$', selected, re.MULTILINE)
        if len(matches) != 1:
            raise ValueError('select exactly one literal ' + name)
        value = ast.literal_eval(matches[0])
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise ValueError('literal list required')
        result.append(value)
    return result


CURRENT = {'BUILD.gn': (args.source / 'BUILD.gn').read_text()}
state = next((index for index, expected in enumerate(HASHES['BUILD.gn'])
              if hashlib.sha256(CURRENT['BUILD.gn'].encode()).hexdigest() == expected), -1)
if state not in (0, 1):
    parser.error('source must be the complete pinned before or after Electron BUILD.gn')
BEFORE = CURRENT if state == 0 else patch_sources(CURRENT, PATCH.read_text(), reverse=True)
AFTER = patch_sources(BEFORE, PATCH.read_text())


class ChecksumSelectionTests(unittest.TestCase):
    def setUp(self):
        self.text = AFTER['BUILD.gn']
        self.context = [['$root_out_dir/$v8_context_snapshot_filename'], ['//tools/v8_context_snapshot']]
        self.ordinary = [['$root_out_dir/snapshot_blob.bin'], ['//v8:run_mksnapshot_default']]

    def test_exact_patch_and_inverse(self):
        self.assertEqual(patch_sources(AFTER, PATCH.read_text(), reverse=True), BEFORE)
        self.assertEqual(hashlib.sha256(self.text.encode()).hexdigest(), HASHES['BUILD.gn'][1])

    def test_both_external_blob_routes_keep_their_producer(self):
        self.assertEqual(checksum_route(self.text, True, True, True), self.context)
        self.assertEqual(checksum_route(self.text, True, True, False), self.ordinary)

    def test_non_external_and_secondary_guards_stay_closed(self):
        for context in (False, True):
            for default in (False, True):
                self.assertIsNone(checksum_route(self.text, False, default, context))
                self.assertIsNone(checksum_route(BEFORE['BUILD.gn'], False, default, context))
            self.assertIsNone(checksum_route(self.text, True, False, context))

    def test_context_only_dependency_guard_is_a_causal_failure(self):
        guard = 'v8_use_external_startup_data && current_toolchain == default_toolchain'
        self.assertEqual(self.text.count(guard), 1)
        mutant = self.text.replace(guard, 'v8_use_external_startup_data && use_v8_context_snapshot && current_toolchain == default_toolchain')
        self.assertNotEqual(checksum_route(mutant, True, True, False), self.ordinary)
        self.assertNotEqual(checksum_route(BEFORE['BUILD.gn'], True, True, False), self.ordinary)

    def test_wrong_ordinary_input_or_producer_is_a_causal_failure(self):
        action = block(self.text, 'action("mksnapshot_checksum_gen") {')
        ordinary = block(action, 'else {')
        for old, new in [('$root_out_dir/snapshot_blob.bin', '$root_out_dir/$v8_context_snapshot_filename'),
                         ('//v8:run_mksnapshot_default', '//tools/v8_context_snapshot')]:
            mutant = self.text.replace(ordinary, ordinary.replace(old, new))
            self.assertNotEqual(checksum_route(mutant, True, True, False), self.ordinary)

    def test_generator_arguments_and_output_stay_the_same(self):
        old = block(BEFORE['BUILD.gn'], 'action("mksnapshot_checksum_gen") {')
        new = block(self.text, 'action("mksnapshot_checksum_gen") {')
        for prefix in ('script = ', 'outputs = ', 'args = ', 'args += '):
            select = lambda body: [line.strip() for line in body.splitlines() if line.strip().startswith(prefix)]
            self.assertEqual(select(old), select(new), prefix)

    def test_checksum_algorithm_header_and_runtime_consumers_are_unchanged(self):
        for name, expected in UNCHANGED.items():
            self.assertEqual(hashlib.sha256((args.source / name).read_bytes()).hexdigest(), expected, name)
        self.assertEqual(set(AFTER), {'BUILD.gn'})


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0], *remaining])
