#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check ABI source wiring. Executable compile/link tests are separate."""
import argparse
from pathlib import Path


def validate(cmake, header, abi):
    assert 'option(SIMPLECPP_GLIBCXX_DEBUG ' in cmake
    assert 'if(SIMPLECPP_GLIBCXX_DEBUG)\n    target_compile_definitions(simplecpp_lib PUBLIC _GLIBCXX_DEBUG)\nendif()' in cmake
    assert 'configure_file(simplecpp-abi.h.in simplecpp-abi.h @ONLY)' in cmake
    assert 'install(FILES simplecpp.h ${CMAKE_CURRENT_BINARY_DIR}/simplecpp-abi.h' in cmake
    assert '$<BUILD_INTERFACE:${CMAKE_CURRENT_BINARY_DIR}>' in cmake
    assert '#include "simplecpp-abi.h"' in header
    assert header.index('#include "simplecpp-abi.h"') < header.index('#include <vector>')
    assert '#cmakedefine01 SIMPLECPP_GLIBCXX_DEBUG' in abi
    assert '#if defined(__GLIBCXX__)' in abi
    assert '# if SIMPLECPP_GLIBCXX_DEBUG' in abi
    assert '#  if !defined(_GLIBCXX_DEBUG)' in abi
    assert '#  if defined(_GLIBCXX_DEBUG)' in abi
    assert abi.count('#   error "simplecpp: libstdc++ debug ABI mismatch"') == 2
    assert '#define _GLIBCXX_DEBUG' not in abi and '#undef _GLIBCXX_DEBUG' not in abi


def check_source(source):
    cmake = (source / 'CMakeLists.txt').read_text()
    header = (source / 'simplecpp.h').read_text()
    abi = (source / 'simplecpp-abi.h.in').read_text()
    validate(cmake, header, abi)
    faults = (
        (cmake.replace('PUBLIC _GLIBCXX_DEBUG', 'PRIVATE _GLIBCXX_DEBUG'), header, abi),
        (cmake, header.replace('#include "simplecpp-abi.h"', ''), abi),
        (cmake, header, abi.replace('#   error "simplecpp: libstdc++ debug ABI mismatch"', '')),
    )
    for fault in faults:
        try:
            validate(*fault)
        except AssertionError:
            pass
        else:
            raise AssertionError('ABI source regression was accepted')
    return {'scope': 'source wiring only; compiler cases are prepared, not executed',
            'negative_controls': ['private definition', 'missing header check', 'removed mismatch errors']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    args = parser.parse_args()
    print(check_source(args.source))
