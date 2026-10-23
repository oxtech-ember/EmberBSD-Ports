#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Exercise pkgsrc iconv selection and the actual upstream shared-XS gate."""
import argparse
import os
import pathlib
import re
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('recipe', type=pathlib.Path)
    parser.add_argument('--pkgsrc', required=True, type=pathlib.Path)
    parser.add_argument('--source', type=pathlib.Path)
    parser.add_argument('--bmake', default=os.environ.get('BMAKE', 'bmake'))
    args = parser.parse_args()
    recipe = (args.recipe / 'Makefile').read_text()
    builtin = (args.pkgsrc / 'converters/libiconv/builtin.mk').read_text()
    policy = ''.join(line for line in recipe.splitlines(True)
                     if re.match(r'^INCOMPAT_ICONV[\s+?=:]', line))
    selection = re.search(r'^\.if !defined\(USE_BUILTIN.iconv\).*?^MAKEVARS\+=\s+USE_BUILTIN.iconv',
                          builtin, re.M | re.S)
    assert selection, 'pkgsrc builtin policy section changed'
    with tempfile.TemporaryDirectory(prefix='texinfo-iconv-') as work:
        fixture = pathlib.Path(work) / 'Makefile'
        fixture.write_text('PREFER.iconv=native\nIS_BUILTIN.iconv=yes\n'
                           'BUILTIN_PKG.iconv=libiconv-1.99\n'
                           'H_GLIBC_ICONV=__nonexistent__\n'
                           'H_CITRUS_ICONV=__nonexistent__\n'
                           'BUILTIN_LIB_FOUND.iconv=yes\n' + policy +
                           selection.group() + '\nall:\n\t@echo ${USE_BUILTIN.iconv}\n')
        for platform in ['Darwin-27.0-arm64', 'Darwin-27.0-x86_64',
                         'NetBSD-11.0-aarch64', 'NetBSD-11.0-x86_64', 'Linux-6.0-x86_64']:
            result = subprocess.run([args.bmake, '-f', str(fixture),
                                     'MACHINE_PLATFORM=' + platform,
                                     'OPSYS=' + platform.split('-')[0]],
                                    check=True, capture_output=True, text=True, timeout=30)
            assert result.stdout.strip() == ('no' if platform.startswith('Darwin-') else 'yes'), platform
    if args.source:
        configure = (args.source / 'tta/configure.ac').read_text()
        decision = re.search(r'^use_shared_txi_libraries=no.*?(?=^AM_CONDITIONAL\(\[USE_SHARED_TXI_LIBRARIES\])',
                             configure, re.M | re.S)
        assert decision, 'upstream shared-library decision changed'
        for working in ['no', 'yes']:
            script = ('am_func_iconv=' + working + '\nenable_xs=yes\n'
                      'enable_additional_tests=no\nwith_swig=no\n' + decision.group() +
                      'printf "%s\\n" "$use_shared_txi_libraries"\n')
            result = subprocess.run(['sh', '-eu'], input=script, text=True,
                                    capture_output=True, check=True, timeout=30)
            assert result.stdout.strip() == working, 'working-iconv gate was bypassed'
    print('PASS: five native provider policies; upstream broken/working iconv gate when source supplied')


if __name__ == '__main__':
    main()
