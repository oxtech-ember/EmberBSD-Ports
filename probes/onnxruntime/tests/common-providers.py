#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check the patched ORT provider selection with installed target CMake configs."""
import argparse
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True, help='patched ONNX Runtime source')
    parser.add_argument('--sysroot', type=Path, required=True, help='target sysroot with common providers')
    parser.add_argument('--cmake', type=Path, required=True, help='selected native CMake executable')
    args = parser.parse_args()
    absl = (args.source / 'cmake/external/abseil-cpp.cmake').resolve(strict=True)
    deps = (args.source / 'cmake/external/onnxruntime_external_deps.cmake').read_text()
    statement = 'find_package(Protobuf CONFIG REQUIRED NAMES protobuf)'
    if deps.count(statement) != 1 or 'onnxruntime_fetchcontent_makeavailable(Protobuf)' in deps:
        raise SystemExit('Protobuf must use the required common provider')
    with tempfile.TemporaryDirectory(prefix='ort-common-providers-') as tmp:
        root = Path(tmp)
        modules = root / 'modules'
        modules.mkdir()
        # This fixture checks only imported metadata; it does not test threads.
        (modules / 'FindThreads.cmake').write_text(
            'set(Threads_FOUND TRUE)\nadd_library(Threads::Threads INTERFACE IMPORTED)\n')
        (root / 'CMakeLists.txt').write_text(f'''cmake_minimum_required(VERSION 3.28)
project(ort_common_provider_metadata NONE)
include(FetchContent)
set(FETCHCONTENT_TRY_FIND_PACKAGE_MODE NEVER)
include("{absl}")
foreach(target IN LISTS ABSEIL_LIBS)
  if(NOT TARGET ${{target}})
    message(FATAL_ERROR "Missing ORT Abseil target ${{target}}")
  endif()
endforeach()
{statement}
if(NOT Protobuf_FOUND OR NOT TARGET protobuf::libprotobuf-lite)
  message(FATAL_ERROR "Missing common protobuf provider")
endif()
''')
        command = [str(args.cmake), '-S', str(root), '-B', str(root / 'out'),
                   '-DCMAKE_SYSTEM_NAME=NetBSD', '-DCMAKE_FIND_ROOT_PATH=' + str(args.sysroot),
                   '-DCMAKE_PREFIX_PATH=/usr/pkg', '-DCMAKE_FIND_ROOT_PATH_MODE_PACKAGE=ONLY',
                   '-DCMAKE_MODULE_PATH=' + str(modules)]
        subprocess.run(command, check=True)
        no_protobuf = list(command)
        no_protobuf[no_protobuf.index(str(root / 'out'))] = str(root / 'no-protobuf')
        no_protobuf.append('-DCMAKE_DISABLE_FIND_PACKAGE_Protobuf=TRUE')
        result = subprocess.run(no_protobuf, capture_output=True, text=True)
        if result.returncode == 0 or 'Protobuf' not in result.stderr:
            raise SystemExit('Missing common protobuf was not rejected')
        # The same patch must fail rather than fetch if common providers are missing.
        command[command.index(str(root / 'out'))] = str(root / 'missing-out')
        command[command.index('-DCMAKE_FIND_ROOT_PATH=' + str(args.sysroot))] = '-DCMAKE_FIND_ROOT_PATH=' + str(root / 'empty')
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode == 0 or 'absl' not in result.stderr:
            raise SystemExit('Missing common Abseil was not rejected')
    print('ORT common provider metadata and missing-provider refusal passed')


if __name__ == '__main__':
    main()
