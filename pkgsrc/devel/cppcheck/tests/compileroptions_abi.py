#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise the Linux/Clang compiler option branch with CMake, without compiling."""
import argparse
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--cmake', type=Path, required=True)
parser.add_argument('--fixture', type=Path, required=True)
parser.add_argument('--patched-module', type=Path, required=True)
parser.add_argument('--original-module', type=Path, required=True)
parser.add_argument('--work', type=Path, required=True)
a = parser.parse_args()
a.work.mkdir()


def configure(name, module, enabled, expected_success, expected_failure=None):
    build = a.work / name
    result = subprocess.run([
        str(a.cmake), '-S', str(a.fixture), '-B', str(build),
        '-DCMAKE_SYSTEM_NAME=Linux', '-DCMAKE_CXX_COMPILER_ID=Clang',
        '-DCPPCHK_GLIBCXX_DEBUG=' + ('ON' if enabled else 'OFF'),
        '-DMODULE=' + str(module),
    ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False,
        timeout=20)
    if (result.returncode == 0) != expected_success:
        raise AssertionError(f'{name}: unexpected CMake result {result.returncode}\n{result.stdout}')
    if expected_failure and expected_failure not in result.stdout:
        raise AssertionError(f'{name}: expected failure marker missing\n{result.stdout}')
    return result.stdout


configure('patched-on', a.patched_module, True, True)
configure('patched-off', a.patched_module, False, True)
configure('original-on-negative-control', a.original_module, True, False,
          'CPPCHK_GLIBCXX_DEBUG=ON must preserve the provider ABI')
print('PASS: patched Linux/Clang module preserves provider ABI when ON and keeps -U when OFF')
print('PASS: original module fails the ON negative control')
print('SCOPE: CMake option evaluation only; no compiler invoked')
