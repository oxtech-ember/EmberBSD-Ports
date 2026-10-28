#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Verify that the producer passes SDK compiler bindings to CMake."""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace

sys.dont_write_bytecode = True
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--sdk-source', required=True)
args = parser.parse_args()
sys.path.insert(0, str(Path(args.sdk_source) / 'src'))
from emberbsd_sdk import compiler_bindings
files = Path(__file__).resolve().parents[1] / 'files'
sys.path.insert(0, str(files))
spec = importlib.util.spec_from_file_location('native_runtime', files / 'native.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
with tempfile.TemporaryDirectory(prefix='libcxx-bindings-') as temporary:
    root = Path(temporary)
    fake = root / 'compiler'
    fake.write_text('#!' + sys.executable + '\nimport json,sys\nprint(json.dumps(sys.argv[1:]))\n')
    fake.chmod(0o755)
    commands = {role: [str(fake), '--selected-' + role] for role in ('cc', 'cxx', 'cpp')}
    flags = dict(cppflags=['-DABI_SELECT=1'], cflags=['-DC_ABI=1'],
                 cxxflags=['-DCXX_ABI=1'], ldflags=['-L', '/selected library'])
    paths = compiler_bindings.bind_compilers(root / 'bindings', commands=commands,
                                              flags=flags, python=sys.executable)
    native = SimpleNamespace(host={'cpu': 'arm64'}, path='/host/bin',
                             tool=lambda name: '/host/bin/' + name)
    opts = mod.cmake_arguments(root, root, Path('/host'), Path('/sdk'), '26.0', native,
                               {'CC': paths['cc'], 'CXX': paths['cxx']})
    values = dict(value[2:].split('=', 1) for value in opts if value.startswith('-D'))
    for role, expected in (('C', '-DC_ABI=1'), ('CXX', '-DCXX_ABI=1')):
        actual = json.loads(subprocess.check_output([values['CMAKE_' + role + '_COMPILER'], '-c', 'fixture.c']))
        assert '-DABI_SELECT=1' in actual and expected in actual
        assert '/selected library' not in actual
print('native CMake bindings retain selected ABI flags PASS')
