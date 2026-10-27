#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Exercise the selected SDK child environment.
import json
import os
from pathlib import Path
import sys
sys.dont_write_bytecode = True
import llvm_sdk as sdk


def test(args):
    if len(args) != 1:
        raise ValueError("usage: test-llvm-sdk-environment.py --sdk-source SDK NEW_TEST_WORK")
    work = Path(sdk.new_destination(args[0]))
    work.mkdir()
    probe = (
        "import json, os, sys; "
        "json.dump({key: os.environ.get(key) for key in "
        "('NATIVE_CXX', 'TMPDIR', 'CXX', 'CXXFLAGS', 'LLVM_ENV_TEST_MARKER')}, "
        "open(sys.argv[1], 'w', encoding='utf-8'))"
    )
    keys = ('NATIVE_CXX', 'CXX', 'CXXFLAGS', 'LLVM_ENV_TEST_MARKER')
    previous = {key: os.environ.get(key) for key in keys}

    def run_case(name, expected_native):
        output = work / (name + '.json')
        log = work / (name + '.log')
        sdk.produce([sys.executable, '-c', probe, str(output)], log)
        observed = json.loads(output.read_text())
        expected_tmpdir = str(work.resolve())
        if observed['NATIVE_CXX'] != expected_native:
            raise ValueError('FAIL: ' + name + ' NATIVE_CXX propagation')
        if observed['TMPDIR'] != expected_tmpdir:
            raise ValueError('FAIL: ' + name + ' TMPDIR override')
        if any(observed[key] is not None for key in ('CXX', 'CXXFLAGS', 'LLVM_ENV_TEST_MARKER')):
            raise ValueError('FAIL: ' + name + ' inherited unrelated compiler environment')
        print('PASS: ' + name + ' selected SDK child environment', flush=True)

    try:
        os.environ['NATIVE_CXX'] = '/fixture/native-clang++'
        os.environ['CXX'] = '/fixture/ambient-cxx'
        os.environ['CXXFLAGS'] = '-DLEAKED_CXXFLAGS'
        os.environ['LLVM_ENV_TEST_MARKER'] = 'must-not-pass'
        run_case('explicit-native-cxx', '/fixture/native-clang++')
        os.environ.pop('NATIVE_CXX')
        run_case('no-native-cxx-override', None)
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    return 0


if __name__ == '__main__':
    sys.exit(sdk.main(test))
