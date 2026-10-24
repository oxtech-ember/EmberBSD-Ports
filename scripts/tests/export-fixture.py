#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD; AI-assisted source regression adapter.
"""Inject explicit test tools into the sole exporter. This is not admission.

Only source regression tests use this adapter. It neither loads a seed nor
qualifies its tools. FAKE_ARCHIVE affects the finite Git fixture only.
"""

import importlib.util
import os
from pathlib import Path
import subprocess
import shutil
import sys
import tarfile

sys.dont_write_bytecode = True


class TestSelection:
    def __init__(self):
        self.tools = {}
        for role in ('git', 'patch'):
            value = os.environ.get('EXPORT_TEST_' + role.upper())
            if not value or not os.path.isabs(value):
                raise ValueError('Set EXPORT_TEST_' + role.upper() + ' to an absolute test tool.')
            self.tools[role] = (value,)

    def command(self, role):
        return self.tools[role]


def test_runner(argv, *, cwd=None, input=None):
    fixture = os.environ.get('FAKE_ARCHIVE')
    if fixture:
        pin = os.environ.get('FAKE_PIN', '1' * 40).encode()
        if 'ls-files' in argv:
            return b'160000 ' + pin + b' 0\tupstream/pkgsrc\n'
        if 'rev-parse' in argv:
            return (pin if os.environ.get('FAKE_MATCH') == '1' else b'2' * 40) + b'\n'
        if 'archive' in argv:
            output = next(word.removeprefix('--output=') for word in argv if word.startswith('--output='))
            with tarfile.open(output, 'w') as stream:
                for path in sorted(Path(fixture).iterdir()):
                    stream.add(path, arcname=path.name)
            return b''
    result = subprocess.run(argv, cwd=cwd, input=input, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, check=True,
                            env={**os.environ, 'LC_ALL': 'C', 'GIT_OPTIONAL_LOCKS': '0',
                                 'GIT_NO_LAZY_FETCH': '1'})
    return result.stdout


def load_exporter(root):
    spec = importlib.util.spec_from_file_location('ports_exporter', Path(root) / 'scripts/prepare-pkgsrc.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if __name__ == '__main__':
    try:
        if len(sys.argv) != 3:
            raise ValueError('Usage: export-fixture.py PORTS_ROOT NEW_DESTINATION')
        destination = Path(sys.argv[2])
        scratch = destination.with_name('.' + destination.name + '.export-scratch')
        load_exporter(sys.argv[1]).export_pkgsrc(sys.argv[1], destination,
            selection=TestSelection(), runner=test_runner, scratch=scratch)
        shutil.rmtree(scratch)
    except Exception as error:
        print('export source regression: ' + str(error), file=sys.stderr)
        if 'scratch' in globals() and scratch.exists():
            print('Retained source-test scratch: ' + str(scratch), file=sys.stderr)
        sys.exit(getattr(error, 'returncode', 2))
