#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'cross'))
spec = spec_from_file_location('helper_tests', Path(__file__).resolve().parents[1] / 'cross/test-llvm-config.py')
module = module_from_spec(spec)
spec.loader.exec_module(module)
assert module.fixture_sysroot({'sysroot': '/original'}, Path('/fixture')) == '/original'
assert module.fixture_sysroot({'sysroot': '/original', 'relocated_installed_prefix': True}, Path('/fixture')) == '/fixture'
print('PASS: strict and relocated synthetic sysroot selection')
