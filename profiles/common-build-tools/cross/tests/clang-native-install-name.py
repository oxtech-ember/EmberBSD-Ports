#!/usr/bin/env python3
"""Check that the native Clang generator configure selects install_name_tool on Darwin."""
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
import argparse
import os
from pathlib import Path
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class Configured(Exception):
    pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk-source', required=True)
    parser.add_argument('--host-prefix', required=True, help='native Ports prefix with LLVM')
    parser.add_argument('--archive', required=True, help='llvm-project-23.1.4.src.tar.xz')
    args = parser.parse_args()
    sys.argv[1:] = ['--sdk-source', args.sdk_source]
    import llvm_host
    llvm_host.load_sdk()
    prefix = args.host_prefix
    os.environ['EMBERBSD_HOST_PREFIX'] = prefix
    commands = []

    def record(path, argv, cwd=None, env=None):
        commands.append(argv)
        raise Configured()

    # Stop at the configure command; the source content is not needed.
    llvm_host.log_run = record
    llvm_host.extract_source = lambda *unused, **kwargs: None
    with tempfile.TemporaryDirectory() as temp:
        try:
            llvm_host.native('clang', [args.archive, prefix, temp + '/work',
                                       prefix + '/bin/cmake', prefix + '/bin/ninja'])
        except Configured:
            pass
    selected = [a for a in commands[0] if a.startswith('-DCMAKE_INSTALL_NAME_TOOL=')]
    if len(selected) != 1 or not os.access(selected[0].split('=', 1)[1], os.X_OK):
        print('FAIL: Darwin CMake configure has no CMAKE_INSTALL_NAME_TOOL')
        return 1
    print('PASS: ' + selected[0])
    return 0


if __name__ == '__main__':
    sys.exit(main())
