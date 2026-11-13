#!/usr/bin/env python3
"""Check the all-output comparison independently of GPU availability."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('diagnostic', Path(__file__).with_name('onnx-runtime-diagnostic.py'))
diag = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diag)

base = [(b'boxes', (1, 2), [1., 2.]), (b'masks', (1, 2), [3., 4.])]
assert diag.compare_outputs(base, base, 0., 0.) == 0
assert diag.compare_outputs(base, [base[0], (b'masks', (1, 2), [3., 5.])], 0., 0.) == 1
assert diag.compare_outputs(base, [base[0], (b'masks', (1, 2), [3., float('nan')])], 0., 0.) == 1
for bad in ([base[0]], [base[0], (b'masks', (2, 1), [3., 4.])]):
    try:
        diag.compare_outputs(base, bad, 0., 0.)
    except RuntimeError:
        pass
    else:
        raise AssertionError('shape/count mismatch accepted')
print('ONNX all-output comparison PASS')
