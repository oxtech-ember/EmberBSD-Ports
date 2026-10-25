#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Refuse incomplete metadata selections before any make child."""
import copy
import importlib.util
import os
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('gzip_source', Path(__file__).with_name('gzip-source.py'))
SOURCE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SOURCE)


class MetadataSelectionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.work, self.pkgsrc = self.root / 'work', self.root / 'pkgsrc'
        for path in (self.work, self.pkgsrc, self.root / 'bin', self.root / 'mk'):
            path.mkdir()
        for name in ('bmake', 'mksh'):
            path = self.root / 'bin' / name
            path.write_text('Synthetic selection only. Do not execute.\n')
            path.chmod(0o755)
        (self.root / 'mk/sys.mk').write_text('# Synthetic system rule.\n')
        self.conf = self.work / 'mk.conf'
        self.conf.write_text('# Private fixture.\n')
        env = {name: str(self.work / name.lower()) for name in
               ('HOME', 'TMPDIR', 'XDG_CACHE_HOME', 'XDG_CONFIG_HOME', 'XDG_DATA_HOME')}
        for name in env.values():
            Path(name).mkdir()
        env.update(PATH=str(self.root / 'bin'), LC_ALL='C', TZ='UTC', MAKECONF=str(self.conf))
        self.selection = dict(make=[str(self.root / 'bin/bmake'), '-m', str(self.root / 'mk'),
            'SHELL=' + str(self.root / 'bin/mksh'), 'MAKECONF=' + str(self.conf)],
            work=str(self.work), environment=env, record=str(self.pkgsrc / 'metadata.json'))

    def test_complete_selection_ignores_ambient_environment(self):
        with patch.dict(os.environ, {'MAKEFLAGS': 'ambient-bad', 'BASH_ENV': '/outside/bad'}):
            argv, env, work, record = SOURCE.metadata_inputs(self.selection, self.pkgsrc)
        self.assertEqual(argv, self.selection['make'])
        self.assertEqual(env, self.selection['environment'])
        self.assertNotIn('MAKEFLAGS', env)
        self.assertEqual(work, self.work)
        self.assertEqual(record, self.pkgsrc / 'metadata.json')

    def test_missing_relative_nonexec_and_escaping_inputs_refuse(self):
        mutants = []
        for index in range(5):
            value = copy.deepcopy(self.selection)
            value['make'].pop(index)
            mutants.append(value)
        for index, word in [(0, 'bmake'), (2, 'mk'), (3, 'SHELL=mksh'), (4, 'MAKECONF=mk.conf')]:
            value = copy.deepcopy(self.selection)
            value['make'][index] = word
            mutants.append(value)
        for index, prefix in [(0, ''), (2, ''), (3, 'SHELL='), (4, 'MAKECONF=')]:
            value = copy.deepcopy(self.selection)
            value['make'][index] = prefix + str(self.root / 'absent')
            mutants.append(value)
        for key in self.selection:
            value = copy.deepcopy(self.selection)
            del value[key]
            mutants.append(value)
        for key in ('HOME', 'TMPDIR', 'MAKECONF', 'PATH'):
            value = copy.deepcopy(self.selection)
            value['environment'][key] = '/outside'
            mutants.append(value)
        value = copy.deepcopy(self.selection)
        value['environment']['MAKEFLAGS'] = 'ambient-bad'
        mutants.append(value)
        nonexec = self.root / 'bin/nonexec'
        nonexec.write_text('No executable mode.\n')
        value = copy.deepcopy(self.selection)
        value['make'][3] = 'SHELL=' + str(nonexec)
        mutants.append(value)
        value = copy.deepcopy(self.selection)
        value['make'][0] = str(nonexec)
        mutants.append(value)
        for value in mutants:
            with self.subTest(value=value), patch.object(SOURCE.subprocess, 'run') as child:
                with self.assertRaises(ValueError):
                    SOURCE.metadata_inputs(value, self.pkgsrc)
                child.assert_not_called()

    def test_success_exit_with_parse_time_warning_is_refused(self):
        selection = self.work / 'selection.json'
        selection.write_text(json.dumps(self.selection))
        result = SimpleNamespace(returncode=0, stdout='gzip-1.15\nyes\nLESS=less\n\n',
                                 stderr='make: warning: parse-time child failed\n')
        args = SimpleNamespace(metadata_selection=selection, pkgsrc=self.pkgsrc)
        with patch.object(SOURCE, 'ARGS', args), patch.object(SOURCE, 'native_metadata', return_value=result):
            with self.assertRaises(AssertionError):
                SOURCE.GzipSourceTests('test_real_native_package_metadata').test_real_native_package_metadata()


if __name__ == '__main__':
    unittest.main()
