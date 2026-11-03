#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Evaluate the compiler-rt atomic package branch with selected bmake."""
import argparse
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bmake', required=True)
    parser.add_argument('--work', type=Path, required=True)
    args = parser.parse_args()
    args.work.mkdir(parents=True)
    recipe = Path(__file__).resolve().parents[1] / 'Makefile'
    text = recipe.read_text()
    start = text.index('.if ${OPSYS} == "NetBSD" && ${USE_CROSS_COMPILE:Uno:tl} == "yes"')
    end = text.index('GENERATE_PLIST+=', start)
    fragment = text[start:end]

    cases = (
        ('riscv32', 'yes', '14', True),
        ('riscv32', 'no', '13', True),
        ('x86_64', 'yes', '13', False),
        ('x86_64', 'no', '12', False),
    )
    for index, (arch, cross, revision, libc_provider) in enumerate(cases):
        fixture = args.work / ('case-' + str(index) + '.mk')
        fixture.write_text('\n'.join((
            'PKGREVISION= 12', 'CMAKE_CONFIGURE_ARGS=', 'INSTALLATION_DIRS=',
            'TEST= test', 'LN= ln', 'INSTALL_DATA=install',
            'FILESDIR=' + str(recipe.parent / 'files'), fragment,
            '.PHONY: vars',
            'vars:',
            '\t@echo REV=${PKGREVISION}',
            '\t@echo CMAKE=${CMAKE_CONFIGURE_ARGS}',
            '\t@echo DIRS=${INSTALLATION_DIRS}',
            '\t@echo ATOMIC=${_COMPILER_RT_ATOMIC:U}',
            '\t@echo TARGETS=${.TARGETS}',
            '')))
        command = [args.bmake, '-r', '-f', str(fixture), 'OPSYS=NetBSD',
                   'MACHINE_ARCH=' + arch, 'USE_CROSS_COMPILE=' + cross, 'vars']
        result = subprocess.run(command, check=True, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        values = dict(line.split('=', 1) for line in result.stdout.splitlines()
                      if '=' in line)
        assert values['REV'] == revision, (arch, cross, values)
        cmake = values['CMAKE']
        dirs = values['DIRS'].split()
        if libc_provider:
            assert '-DCOMPILER_RT_EXCLUDE_ATOMIC_BUILTIN=ON' in cmake, values
            assert '-DCOMPILER_RT_BUILD_STANDALONE_LIBATOMIC=OFF' in cmake, values
            assert '-DCOMPILER_RT_BUILD_STANDALONE_LIBATOMIC=ON' not in cmake, values
            assert dirs == ['lib'] and not values['ATOMIC'], values
            target = subprocess.run([args.bmake, '-r', '-f', str(fixture),
                                     'OPSYS=NetBSD', 'MACHINE_ARCH=' + arch,
                                     'USE_CROSS_COMPILE=' + cross, '-n', 'post-install'],
                                    text=True, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            assert target.returncode == 0, target.stderr
            assert 'libatomic-libc.ldscript' in target.stdout, target.stdout
            assert 'libatomic.so' in target.stdout and 'libatomic.a' in target.stdout, target.stdout
            stage = args.work / ('stage-' + str(index))
            (stage / 'usr/pkg/lib').mkdir(parents=True)
            installed = subprocess.run(
                [args.bmake, '-r', '-f', str(fixture), 'OPSYS=NetBSD',
                 'MACHINE_ARCH=' + arch, 'USE_CROSS_COMPILE=' + cross,
                 'PREFIX=/usr/pkg', 'DESTDIR=' + str(stage), 'post-install'],
                check=True, text=True, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
            for suffix in ('a', 'so'):
                path = stage / 'usr/pkg/lib' / ('libatomic.' + suffix)
                assert path.read_bytes() == (recipe.parent / 'files/libatomic-libc.ldscript').read_bytes(), path
        else:
            assert '-DCOMPILER_RT_BUILD_STANDALONE_LIBATOMIC=ON' in cmake, values
            assert '-DCOMPILER_RT_EXCLUDE_ATOMIC_BUILTIN=ON' not in cmake, values
            assert dirs == ['lib'] and values['ATOMIC'], values
            target = subprocess.run([args.bmake, '-r', '-f', str(fixture),
                                     'OPSYS=NetBSD', 'MACHINE_ARCH=' + arch,
                                     'USE_CROSS_COMPILE=' + cross, '-n', 'post-install'],
                                    check=True, text=True, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            assert 'libatomic.so' in target.stdout, target.stdout
    print('PASS: bmake selects libc atomics only for RV32; compiler-rt libatomic remains on other NetBSD architectures')


if __name__ == '__main__':
    main()
