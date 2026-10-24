#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Build a copy of configured Texinfo C sources with format errors enabled."""
import argparse
import pathlib
import re
import shutil
import subprocess

DECLARATIONS = {
    'main/text.h': r'void text_printf \(TEXT \*t, const char \*format, \.\.\.\)\s*'
                   r'TXI_PRINTF_FORMAT \(2, 3\);',
    'main/utils.h': r'int xasprintf \(char \*\*ptr, const char \*template, \.\.\.\)\s*'
                    r'TXI_PRINTF_FORMAT \(2, 3\);',
}
PROBE = '''#include <stdint.h>
#include "text.h"
void probe (TEXT *t, uint32_t code_point)
{
  text_printf (t, "%04lx", CODE_POINT);
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=pathlib.Path,
                        help='configured texinfo-7.3 build directory')
    parser.add_argument('work', type=pathlib.Path, help='new scratch directory')
    parser.add_argument('--cc', required=True, help='package C compiler')
    parser.add_argument('--make', default='gmake')
    args = parser.parse_args()
    source = args.source.resolve(strict=True)
    tta = source / 'tta'
    args.work.mkdir()
    work = args.work.resolve()
    for name, declaration in DECLARATIONS.items():
        text = (tta / 'C' / name).read_text()
        assert re.search(declaration, text), name + ' lost its printf format check'

    probe = work / 'probe.c'
    probe.write_text(PROBE)
    for argument, success in [('code_point', False), ('(unsigned long) code_point', True)]:
        result = subprocess.run([args.cc, '-fsyntax-only', '-Werror=format',
                                 '-I', str(tta / 'C' / 'main'),
                                 '-DCODE_POINT=' + argument, str(probe)],
                                capture_output=True, text=True, timeout=60)
        assert (result.returncode == 0) == success, result.stderr
        if not success:
            assert '-Werror=format' in result.stderr, result.stderr

    copy = work / 'texinfo' / 'tta'
    shutil.copytree(source, copy.parent, symlinks=True)
    subprocess.run([args.make, '-C', str(copy / 'C'), 'clean'], check=True,
                   capture_output=True, timeout=300)
    result = subprocess.run([args.make, '-C', str(copy / 'C'),
                             'CFLAGS=-O2 -Werror=format'],
                            capture_output=True, text=True, timeout=1800)
    log = result.stdout + result.stderr
    assert result.returncode == 0, log[-4000:]
    assert '-Wformat' not in log.replace('-Werror=format', ''), log[-4000:]
    print('PASS: Texinfo C sources build with -Werror=format; the probe rejects '
          'a 32-bit code point for %lx')


if __name__ == '__main__':
    main()
