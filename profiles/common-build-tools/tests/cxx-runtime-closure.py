#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Check the actual package dependency expressions and pkg_admin version matching."""
import pathlib
import subprocess
import sys
import tempfile

bmake, pkg_admin, root = sys.argv[1:]
root = pathlib.Path(root)
recipe = (root / 'pkgsrc/lang/compiler-rt/runtime-package.mk').read_text()
recipe = '\n'.join(line for line in recipe.splitlines() if not line.startswith('.include '))
with tempfile.TemporaryDirectory() as tmp:
    makefile = pathlib.Path(tmp) / 'Makefile'
    makefile.write_text('LLVM_VERSION=23.1.4\n' + recipe + '\n')
    for component in ('libunwind', 'libcxxabi', 'libcxx'):
        for devel in (False, True):
            args = [bmake, '-f', str(makefile), f'EMBER_LLVM_CXX_COMPONENT={component}',
                    'USE_CROSS_COMPILE=yes', 'OPSYS=NetBSD', 'MACHINE_ARCH=aarch64',
                    '-V', '${PKGREVISION}', '-V', '${DEPENDS}']
            if devel:
                args.insert(4, 'EMBER_LLVM_CXX_DEVEL=yes')
            revision, dependencies = subprocess.check_output(args, text=True).splitlines()
            assert revision == '2', (component, devel, revision)
            if component != 'libunwind':
                assert 'libunwind>=23.1.4nb2:' in dependencies, dependencies
            if devel:
                assert f'{component}>=23.1.4nb2:' in dependencies, dependencies
                if component != 'libunwind':
                    assert 'libunwind-devel>=23.1.4nb2:' in dependencies, dependencies
            if component == 'libcxx':
                assert 'libcxxabi>=23.1.4nb2:' in dependencies, dependencies
                if devel:
                    assert 'libcxxabi-devel>=23.1.4nb2:' in dependencies, dependencies
    for component in ('libunwind', 'libcxxabi', 'libcxx'):
        for suffix in ('', '-devel'):
            pattern = f'{component}{suffix}>=23.1.4nb2'
            for revision, expected in ((1, 1), (2, 0)):
                actual = subprocess.run([pkg_admin, 'pmatch', pattern,
                                         f'{component}{suffix}-23.1.4nb{revision}'],
                                        stdout=subprocess.DEVNULL).returncode
                assert actual == expected, (pattern, revision, actual)
        buildlink = (root / f'pkgsrc/lang/{component}/buildlink3.mk').read_text()
        assert f'{component}-devel>=23.1.4nb2' in buildlink
    application = (root / 'pkgsrc/lang/compiler-rt/application-runtime.mk').read_text()
    for component in ('libunwind', 'libcxxabi', 'libcxx'):
        for suffix in ('', '-devel'):
            assert f'{component}{suffix}>=${{_EMBER_TARGET_RUNTIME_VERSION}}nb2:' in application
print('PASS: six runtime packages, dependency closure, buildlinks and version matching')
