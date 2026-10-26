#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""The old builtins CLI delegates to the single patched compiler-rt producer."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
PORTS = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PORTS / 'pkgsrc/lang/llvm/files'))
from sdk_source import load_sdk
_, arguments = load_sdk()
spec = importlib.util.spec_from_file_location('builtins_adapter', PORTS / 'pkgsrc/lang/llvm/files/build-builtins.py')
producer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(producer)
from emberbsd_sdk import jsonio
from emberbsd_sdk.errors import CommandError


class BuiltinsCompatibility(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='builtins-adapter-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.work = self.root / 'work'
        self.options = SimpleNamespace(plan=False, archive='/selected/archive', git='/selected/git')
        self.args = SimpleNamespace(source=str(self.work/'source'), stage=str(self.work/'stage'),
                                    work=str(self.work/'build'), phase='builtins')
        self.result = dict(format='emberbsd-builtins-build', version=1, work=str(self.work),
                           status='planned', target_execution='not-run')
        self.calls = []
        def prepare(archive, source, patch_tool, git):
            self.calls.append(('prepare', archive, source, patch_tool, git))
            Path(source).mkdir()
            (Path(source)/'llvm-source.json').write_text('prepared by the common patch owner')
        self.owner = SimpleNamespace(jsonio=jsonio, prepare_source=prepare)
        def build(owner, args):
            self.assertIs(owner, self.owner)
            self.assertEqual(args.phase, 'builtins')
            self.assertTrue((Path(args.source)/'llvm-source.json').is_file())
            self.calls.append(('build', args.source, args.stage))
            return {'components':['builtins']}
        self.common = SimpleNamespace(build=build)

    def inputs(self):
        return copy.deepcopy(self.result), self.owner, self.common, self.args, '/selected/patch'

    def test_existing_cli_prepares_patched_source_then_calls_shared_builtins_phase(self):
        with patch.object(producer, '_inputs', side_effect=lambda options: self.inputs()):
            result = producer.build(self.options)
        self.assertEqual([call[0] for call in self.calls], ['prepare','build'])
        self.assertEqual(result['status'], 'built-and-inspected')
        self.assertEqual(result['runtime'], {'components':['builtins']})
        self.assertEqual(json.loads((self.work/'build.json').read_text()), result)

    def test_read_only_plan_does_not_extract_create_work_or_build(self):
        self.options.plan = True
        with patch.object(producer, '_inputs', side_effect=lambda options: self.inputs()):
            self.assertEqual(producer.build(self.options), self.result)
        self.assertFalse(self.work.exists())
        self.assertEqual(self.calls, [])

    def test_failed_shared_command_preserves_status_without_completed_manifest(self):
        def fail(owner, args):
            Path(args.stage).mkdir()
            (Path(args.stage)/'runtime.json').write_text('incomplete')
            raise CommandError(7, ['selected-cmake'])
        self.common.build = fail
        with patch.object(producer, '_inputs', side_effect=lambda options: self.inputs()), \
             self.assertRaises(CommandError) as error:
            producer.build(self.options)
        self.assertEqual(error.exception.returncode, 7)
        self.assertFalse((Path(self.args.stage)/'runtime.json').exists())
        self.assertEqual(json.loads((self.work/'build.json').read_text())['status'], 'failed')


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0], *arguments], verbosity=2)
