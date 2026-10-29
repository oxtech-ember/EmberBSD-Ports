#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'cross'))
spec = spec_from_file_location('sealer', Path(__file__).resolve().parents[1] / 'cross/seal-llvm-config.py')
module = module_from_spec(spec)
spec.loader.exec_module(module)
assert module.output_argument(['clang++', '-o', '/tmp/result', '-L/selected']) == '/tmp/result'
for argv in (['clang++'], ['clang++', '-o'], ['clang++', '-o', 'one', '-o', 'two']):
    try:
        module.output_argument(argv)
    except ValueError as exc:
        assert 'output argument' in str(exc)
    else:
        raise AssertionError('invalid output argument accepted')
print('PASS: reordered output and missing/duplicate output refusal')
