#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Check patched Node Python routes. Never execute Node or GN."""
import argparse
import hashlib
import os
from pathlib import Path
import re
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

SOURCE = None
JS_SHA256 = None


def module(name, relative):
    path = SOURCE / relative
    value = types.ModuleType(name)
    value.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), 'exec'), value.__dict__)
    return value


class QualifiedNodeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name).resolve()
        self.executable = self.work / "selected node's $literal;tool"
        self.executable.write_bytes(b'fixture data, never executed\n')
        self.executable.chmod(0o755)
        self.node = module('qualified_node_fixture', 'third_party/node/node.py')
        with patch.dict(sys.modules, {'node': self.node}):
            self.check = module('node_version_fixture', 'third_party/node/check_version.py')

    def env(self, value=None):
        values = {} if value is None else {'EMBERBSD_HOST_NODE': value}
        return patch.dict(os.environ, values, clear=True)

    def arguments(self, output):
        return ['--expected_version_file', str(SOURCE / 'third_party/node/update_node_binaries'),
                '--out_file', str(output)]

    def test_default_host_routes_remain_source_owned(self):
        cases = [('Darwin', 'arm64', 'mac_arm64/node-darwin-arm64/bin/node'),
                 ('Darwin', 'x86_64', 'mac/node-darwin-x64/bin/node'),
                 ('Linux', 'x86_64', 'linux/node-linux-x64/bin/node'),
                 ('FreeBSD', 'aarch64', 'freebsd/node-freebsd/bin/node'),
                 ('OpenBSD', 'amd64', 'openbsd/node-openbsd/bin/node'),
                 ('NetBSD', 'aarch64', 'netbsd/node-netbsd/bin/node'),
                 ('Windows', 'AMD64', 'win/node.exe')]
        for host, cpu, relative in cases:
            with self.subTest(host=host, cpu=cpu), self.env(), \
                    patch.object(self.node.platform, 'system', return_value=host), \
                    patch.object(self.node.platform, 'machine', return_value=cpu):
                self.assertEqual(self.node.GetBinaryPath(), str(SOURCE / 'third_party/node' / relative))

    def test_explicit_executable_preserves_one_path_and_all_arguments(self):
        arguments = ['script with spaces.js', '--value', "literal;'$(not-a-command)"]
        process = Mock(returncode=0)
        process.communicate.return_value = ('ok', '')
        with self.env(str(self.executable)), patch.object(self.node.subprocess, 'Popen', return_value=process) as child:
            self.assertEqual(self.node.GetBinaryPath(), str(self.executable))
            self.assertEqual(self.node.RunNodeRaw(arguments), (0, 'ok', ''))
        self.assertEqual(child.call_args.args[0], [str(self.executable)] + arguments)
        self.assertIs(child.call_args.kwargs.get('shell', False), False)

    def test_invalid_explicit_paths_never_start_a_fallback(self):
        directory = self.work / 'directory'; directory.mkdir()
        plain = self.work / 'non-executable'; plain.write_bytes(b'data'); plain.chmod(0o644)
        broken = self.work / 'broken'; broken.symlink_to('missing')
        for candidate in ('', 'relative/node', str(self.work / 'missing'),
                          str(directory), str(plain), str(broken)):
            with self.subTest(candidate=candidate), self.env(candidate), \
                    patch.object(self.node.subprocess, 'Popen') as child:
                with self.assertRaises(RuntimeError):
                    self.node.RunNodeRaw(['--version'])
                child.assert_not_called()

    def test_explicit_in_bundle_alias_can_name_the_same_executable(self):
        alias = self.work / 'node-alias'; alias.symlink_to(self.executable.name)
        with self.env(str(alias)):
            self.assertEqual(self.node.GetBinaryPath(), str(alias))

    def test_selected_version_uses_the_fixed_common_version_input(self):
        output = self.work / 'selected-result'
        with self.env(str(self.executable)), patch.object(self.node, 'RunNode') as run:
            self.check.main(self.arguments(output))
        expected = SOURCE / 'third_party/node/emberbsd_host_node_version'
        self.assertRegex(expected.read_text(), r'(?m)^NODE_VERSION="v24\.22\.0"$')
        run.assert_called_once_with([str(SOURCE / 'third_party/node/check_version.js'),
                                     '--expected_version_file', str(expected)])
        self.assertEqual(output.read_text(), 'OK')

    def test_unset_version_uses_the_original_upstream_input(self):
        output = self.work / 'default-result'
        expected = SOURCE / 'third_party/node/update_node_binaries'
        with self.env(), patch.object(self.node, 'RunNode') as run:
            self.check.main(self.arguments(output))
        run.assert_called_once_with([str(SOURCE / 'third_party/node/check_version.js'),
                                     '--expected_version_file', str(expected)])
        self.assertRegex(expected.read_text(), r'(?m)^NODE_VERSION="v24\.12\.0"$')

    def test_version_failure_cannot_write_a_success_marker(self):
        output = self.work / 'must-not-exist'
        with self.env(str(self.executable)), \
                patch.object(self.node, 'RunNode', side_effect=RuntimeError('version mismatch')) as run:
            with self.assertRaisesRegex(RuntimeError, 'version mismatch'):
                self.check.main(self.arguments(output))
        run.assert_called_once()
        self.assertFalse(output.exists())

    def test_invalid_selector_cannot_write_a_success_marker(self):
        output = self.work / 'must-not-exist'
        with self.env(str(self.work / 'missing')), patch.object(self.node.subprocess, 'Popen') as child:
            with self.assertRaises(RuntimeError):
                self.check.main(self.arguments(output))
        child.assert_not_called()
        self.assertFalse(output.exists())

    def test_original_javascript_equality_check_remains_exact(self):
        source = SOURCE / 'third_party/node/check_version.js'
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), JS_SHA256)
        self.assertIn('assert.equal(expectedVersion, process.version, errorMessage);', source.read_text())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    args, remaining = parser.parse_known_args()
    SOURCE = args.source.resolve(strict=True)
    # Pinned Chromium dd78960 has this unchanged JavaScript exact check.
    JS_SHA256 = '54bfaa4865e9972f3046042adc18fc94d4834fa6705df63f8403aac109302086'
    unittest.main(argv=[sys.argv[0], *remaining])
