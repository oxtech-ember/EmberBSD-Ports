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


def output(shape, values, name=b'rows'):
    return [(name, shape, values)]


def compare(a, b, atol=0., rtol=0., names=('rows',)):
    return diag.compare_outputs(a, b, atol, rtol, names)

# Reorder only the selected output; ordered mode still detects the same change.
a = output((1, 3, 2), [1., 2., 3., 4., 5., 6.])
b = output((1, 3, 2), [5., 6., 1., 2., 3., 4.])
assert compare(a, b) == 0
assert diag.compare_outputs(a, b, 0., 0.) > 0
# Matching must respect multiplicity, even when one candidate matches twice.
assert compare(output((1, 2, 1), [1., 1.]), output((1, 2, 1), [1., 2.])) == 1
# Greedy fails: first row can take either candidate, second only the first.
assert compare(output((1, 2, 1), [0.5, 0.0]), output((1, 2, 1), [0.0, 1.0]), atol=0.5) == 0
assert compare(output((1, 2, 1), [1., 2.]), output((1, 2, 1), [1., 9.])) == 1
assert compare(output((1, 1, 2), [10., 20.]), output((1, 1, 2), [11., 22.]), rtol=0.1) == 0
assert compare(output((1, 1, 2), [10., 20.]), output((1, 1, 2), [11., 23.]), rtol=0.1) == 1
assert compare(output((1, 1, 1), [float('nan')]), output((1, 1, 1), [float('nan')])) == 1
assert compare(output((1, 1, 1), [1.]), output((1, 1, 1), [float('inf')])) == 1
# Rows may never cross batch boundaries.
assert compare(output((2, 1, 1), [1., 2.]), output((2, 1, 1), [2., 1.])) == 2
# A separate mask output remains ordered.
masked_a = a + [(b'masks', (1, 2), [3., 4.])]
masked_b = b + [(b'masks', (1, 2), [4., 3.])]
assert compare(masked_a, masked_b) == 2
for shape, names in [((1, 2), ('rows',)), ((1, 1025, 1), ('rows',)), ((1, 1, 1), ('missing',))]:
    n = 1
    for dim in shape: n *= dim
    try:
        compare(output(shape, [0.] * n), output(shape, [0.] * n), names=names)
    except RuntimeError:
        pass
    else:
        raise AssertionError('invalid unordered selection accepted')
print('ONNX unordered row comparison PASS')
