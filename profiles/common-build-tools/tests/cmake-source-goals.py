#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check that source goals do not require native CMake build tools."""
import argparse
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bmake', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--policy', type=Path, default=
                        Path(__file__).resolve().parents[1] / 'cmake-binutils.mk')
    args = parser.parse_args()
    bmake = args.bmake.resolve(strict=True)
    policy = args.policy.resolve(strict=True)
    goals = ('fetch', 'checksum', 'checksum-phase', 'makesum', 'makepatchsum',
             'distinfo', 'fetch-list', 'fetch-list-one-package',
             'fetch-list-recursive', 'mirror-distfiles', 'show-distfiles',
             'depends-fetch', 'depends-checksum')
    with tempfile.TemporaryDirectory(dir=args.work.resolve(strict=True)) as tmp:
        fragment = Path(tmp) / 'scope.mk'
        fragment.write_text('OPSYS= Darwin\nUSE_CROSS_COMPILE= no\n'
                            '_USE_CWRAPPERS= yes\n'
                            'WRAPPER_BINDIR= ' + tmp + '/generated-wrappers\n'
                            '.include "' + str(policy) + '"\n')

        def query(variable, targets, extra=()):
            return subprocess.check_output(
                [str(bmake), '-f', str(fragment), *extra, '-v', variable,
                 *targets], text=True).strip()

        for target in goals:
            assert not query('PKG_FAIL_REASON', [target]), target
            assert not query('_EMBERBSD_CMAKE_BINUTILS_ARGS', [target]), target
        assert not query('PKG_FAIL_REASON', ['fetch', 'checksum'])
        for targets in ([], ['configure'], ['build'], ['all'], ['install'],
                        ['fetch', 'configure'], ['checksum', 'build'],
                        ['custom-build']):
            reasons = query('PKG_FAIL_REASON', targets)
            assert 'PKG_AR' in reasons and 'OSX_SDK_PATH' in reasons, targets

        # Labelled metadata inputs: no tool is executed or used to compile.
        selected = ['PKG_' + role + '=' + str(bmake)
                    for role in ('AR', 'RANLIB', 'NM', 'STRIP', 'LD')]
        selected += ['OSX_SDK_PATH=' + tmp,
                     'EMBERBSD_DARWIN_INSTALL_NAME_TOOL=' + str(bmake),
                     'EMBERBSD_DARWIN_TAPI=' + str(bmake),
                     'EMBERBSD_DARWIN_TAPI_KIND= llvm-readtapi']
        assert not query('PKG_FAIL_REASON', ['configure'], selected)
        assert '-DCMAKE_AR:FILEPATH=' + str(bmake) in query(
            '_EMBERBSD_CMAKE_BINUTILS_ARGS', ['configure'], selected)
        cross = ['USE_CROSS_COMPILE=yes',
                 'EMBERBSD_CROSS_CMAKE_ARGS=-DCMAKE_SYSTEM_NAME=NetBSD']
        assert query('_EMBERBSD_CMAKE_BINUTILS_ARGS', ['configure'], cross) == \
            '-DCMAKE_SYSTEM_NAME=NetBSD'
    print('PASS: source goals omit native build checks; default, mixed and custom build goals retain them')
    print('PASS: selected native tools and cross routing remain available for configure')


if __name__ == '__main__':
    main()
