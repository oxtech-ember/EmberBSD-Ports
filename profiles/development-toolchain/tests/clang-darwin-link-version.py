#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Check Clang's Darwin linker-version configuration using upstream CMake.

Run with --source LLVM_PROJECT_SOURCE --cmake SELECTED_CMAKE --shell SELECTED_SHELL.
Set TMPDIR to a directory inside the build workspace.
"""
import argparse
import pathlib
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('--source', type=pathlib.Path, required=True)
parser.add_argument('--cmake', type=pathlib.Path, required=True)
parser.add_argument('--shell', type=pathlib.Path, required=True)
args = parser.parse_args()
source = (args.source / 'clang/CMakeLists.txt').read_text()
start = source.index('# Determine HOST_LINK_VERSION on Darwin.')
end = source.index('\ninclude(AddClang)', start)
block = source[start:end]
module = args.source / 'cmake/Modules/GetDarwinLinkerVersion.cmake'
with tempfile.TemporaryDirectory() as temporary:
    root = pathlib.Path(temporary)
    wrapper = root / 'ld'
    marker = root / 'probed'
    wrapper.write_text('#!' + str(args.shell) + '\necho probe > "' + str(marker) + '"\necho ld64-27037.1\n')
    wrapper.chmod(0o755)
    for linker, explicit, expected, probe in [
        ('lld', '', '', False), ('', '', '27037.1', True),
        ('lld', '777.1', '777.1', False),
    ]:
        marker.unlink(missing_ok=True)
        script = root / 'check.cmake'
        script.write_text('set(APPLE TRUE)\nset(CMAKE_LINKER "' + str(wrapper) + '")\n'
                          'set(CLANG_DEFAULT_LINKER "' + linker + '")\n'
                          'set(HOST_LINK_VERSION "' + explicit + '" CACHE STRING "")\n'
                          'include("' + str(module) + '")\n' + block + '\n'
                          'file(WRITE "' + str(root / 'result') + '" "${HOST_LINK_VERSION}")\n')
        subprocess.run([str(args.cmake), '-P', str(script)], check=True,
                       stdout=subprocess.DEVNULL)
        actual = (root / 'result').read_text()
        assert (actual, marker.exists()) == (expected, probe), (linker, explicit, actual, marker.exists())
print('Darwin linker-version configuration: PASS')
