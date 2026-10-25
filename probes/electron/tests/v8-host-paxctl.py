#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted), not submitted upstream.
"""Check the host snapshot PaX source. Never execute GN or a native command."""
import argparse
from contextlib import redirect_stderr
import hashlib
import io
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest import mock

sys.dont_write_bytecode = True
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, required=True, help='Pinned V8 source before or after this patch')
args, remaining = parser.parse_known_args()
PATCH = Path(__file__).resolve().parents[1] / 'patches/v8-host-paxctl.patch'
HASHES = {
    'BUILD.gn': ('0cc77a2aa1a9d91a1e55eeb143f45bd38785165d0063e37e5bab49fbfccf9f34',
                 '1cf885dad280841e415801a3dda03b6d93c250501132c64a57ee0ce4e77894f6'),
    'tools/run-paxctl.py': ('f291e57bb6910fe1c5d4e4b3433962721efd62bca3962f0cc9261eacd087156b',
                            '0c4e5ac3a8992dcf1627ac7fa1fe219d507bf756b618da6b8010c4cb9fbf60aa'),
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
        raise ValueError('patch must change only the selected V8 BUILD.gn and wrapper')
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


def dependency_scope(text):
    action = block(text, 'action("run_mksnapshot_" + name) {')
    found = re.findall(r'if \((host_os|current_os|target_os) == "netbsd"\) \{([^}]+)\}', action)
    found = [name for name, body in found if '":run_paxctl_mksnapshot"' in body]
    if len(found) != 1:
        raise ValueError('select exactly one PaX dependency scope')
    return found[0]


def action_scope(text):
    found = re.findall(r'if \((host_os|current_os|target_os) == "netbsd"\) \{\s*assert\(v8_host_paxctl[^{}]+action\("run_paxctl_mksnapshot"\)', text)
    if len(found) != 1:
        raise ValueError('select exactly one PaX action scope')
    return found[0]


def selected(scope, host, current, target):
    """Inspect the fixed equality guard. This is not a GN evaluator."""
    return {'host_os': host, 'current_os': current, 'target_os': target}[scope] == 'netbsd'


CURRENT = {name: (args.source / name).read_text() for name in HASHES}
states = {next((i for i, expected in enumerate(HASHES[name])
                if hashlib.sha256(text.encode()).hexdigest() == expected), -1)
          for name, text in CURRENT.items()}
if states not in ({0}, {1}):
    parser.error('source must be the complete pinned before or after V8 files')
BEFORE = CURRENT if states == {0} else patch_sources(CURRENT, PATCH.read_text(), reverse=True)
AFTER = patch_sources(BEFORE, PATCH.read_text())


class HostPaxctlTests(unittest.TestCase):
    def setUp(self):
        self.text = AFTER['BUILD.gn']

    def invoke_wrapper(self, text, command, status=0):
        with tempfile.TemporaryDirectory(prefix='v8-paxctl-source-') as directory:
            stamp = Path(directory) / 'stamp'
            argv = ['run-paxctl.py', str(stamp), *command]
            with mock.patch.object(sys, 'argv', argv), mock.patch('subprocess.call', return_value=status) as call, redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as caught:
                    exec(compile(text, 'run-paxctl.py', 'exec'), {'__name__': '__main__'})
            return caught.exception.code, call.call_args_list, stamp.exists()

    def test_exact_patch_and_inverse(self):
        self.assertEqual(patch_sources(AFTER, PATCH.read_text(), reverse=True), BEFORE)
        for name, text in AFTER.items():
            self.assertEqual(hashlib.sha256(text.encode()).hexdigest(), HASHES[name][1])

    def test_action_and_dependency_follow_host_not_target_or_current(self):
        for scope in (action_scope(self.text), dependency_scope(self.text)):
            for host in ('mac', 'linux', 'netbsd'):
                for current in ('mac', 'linux', 'netbsd'):
                    for target in ('mac', 'linux', 'netbsd'):
                        self.assertEqual(selected(scope, host, current, target), host == 'netbsd')

    def test_old_target_guard_is_a_causal_failure(self):
        old_scope, new_scope = dependency_scope(BEFORE['BUILD.gn']), dependency_scope(self.text)
        self.assertTrue(selected(old_scope, 'mac', 'netbsd', 'netbsd'))
        self.assertFalse(selected(new_scope, 'mac', 'netbsd', 'netbsd'))
        self.assertFalse(selected(old_scope, 'netbsd', 'linux', 'linux'))
        self.assertTrue(selected(new_scope, 'netbsd', 'linux', 'linux'))

    def test_target_or_current_guard_mutants_fail_the_host_oracle(self):
        for other in ('target_os', 'current_os'):
            mutant = self.text.replace('if (host_os == "netbsd")', 'if (' + other + ' == "netbsd")')
            for scope in (action_scope(mutant), dependency_scope(mutant)):
                self.assertNotEqual(selected(scope, 'mac', 'netbsd', 'netbsd'), False)
                self.assertNotEqual(selected(scope, 'netbsd', 'linux', 'linux'), True)

    def test_selected_path_is_required_and_declared_without_an_ambient_fallback(self):
        self.assertIn('v8_host_paxctl = ""', self.text)
        self.assertIn('assert(v8_host_paxctl != "",', self.text)
        action = block(self.text, 'action("run_paxctl_mksnapshot") {')
        self.assertIn('inputs = [ v8_host_paxctl ]', action)
        self.assertIn('      v8_host_paxctl,\n      "+m",', action)
        self.assertNotIn('/usr/sbin/paxctl', action)
        self.assertIn('deps = [ ":mksnapshot($v8_snapshot_toolchain)" ]', action)
        self.assertIn('get_label_info(":mksnapshot($v8_snapshot_toolchain)",', action)
        generator = block(self.text, 'action("run_mksnapshot_" + name) {')
        self.assertIn('deps = [ ":mksnapshot($v8_snapshot_toolchain)" ]', generator)

    def test_wrapper_refuses_missing_and_relative_paths_before_any_child(self):
        for command in ([], [''], ['paxctl', '+m', './mksnapshot'], ['../bin/paxctl', '+m', './mksnapshot']):
            status, calls, stamped = self.invoke_wrapper(AFTER['tools/run-paxctl.py'], command)
            self.assertEqual((status, calls, stamped), (2, [], False))

    def test_wrapper_relative_path_refusal_is_causal(self):
        command = ['paxctl', '+m', './mksnapshot']
        old = self.invoke_wrapper(BEFORE['tools/run-paxctl.py'], command)
        new = self.invoke_wrapper(AFTER['tools/run-paxctl.py'], command)
        self.assertEqual(old[0], 0)
        self.assertTrue(old[1])
        self.assertEqual(new, (2, [], False))

    def test_wrapper_preserves_one_absolute_path_argument_and_child_failure(self):
        command = ['/accepted/sdk with spaces/bin/paxctl', '+m', './gcc_arm64_v8_x64/mksnapshot']
        for expected in (0, 7, 127):
            status, calls, stamped = self.invoke_wrapper(AFTER['tools/run-paxctl.py'], command, expected)
            self.assertEqual(status, expected)
            self.assertEqual(calls, [mock.call(command)])
            self.assertTrue(stamped)

    def test_snapshot_toolchain_contract_stays_unchanged(self):
        source = args.source / 'gni/snapshot_toolchain.gni'
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),
                         'a991fe1579543cc75e60335b7a0f8e9c95a52956406004aa8528aeb4787ec3d7')
        self.assertEqual(set(AFTER), {'BUILD.gn', 'tools/run-paxctl.py'})


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0], *remaining])
