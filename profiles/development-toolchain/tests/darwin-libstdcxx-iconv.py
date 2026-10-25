#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Darwin libstdc++ must use the macOS iconv, so -static-libstdc++ needs nothing extra.

Without --cxx, check the recipe sources only. With --cxx, link a std::format
program that pulls the libstdc++ iconv code with -static-libstdc++ and no iconv
option, run it, and check its load commands. GCC built by the previous recipe
selects GNU libiconv from ${LOCALBASE}/lib and fails with undefined libiconv_*.
"""

import argparse
from pathlib import Path
import re
import shlex
import subprocess
import sys

PROFILE = Path(__file__).resolve().parents[1]
ROOT = PROFILE.parents[1]
PROGRAM = r'''#include <chrono>
#include <format>
#include <locale>
#include <string>
int main()
{
  // Locale chrono formatting converts the locale encoding to UTF-8 (iconv).
  std::string s = std::format(std::locale::classic(), "{:L%a}", std::chrono::Monday);
  return s == "Mon" ? 0 : 1;
}
'''


def check_sources(root):
    recipe = (root / 'profiles/development-toolchain/patches/gcc-darwin-host.patch').read_text()
    # The Darwin target libraries must not search ${LOCALBASE}/lib.
    blocks = re.findall(r'\n\+\.if \$\{OPSYS\} == "Darwin"\n((?:\+[^\n]*\n)+)', recipe)
    assert any('+GCC16_TARGET_LDFLAGS=\t${LDFLAGS:M-Wl,-z*}\n' in block and
               '+.else\n+GCC16_TARGET_LDFLAGS=\t${LDFLAGS_FOR_TARGET}\n+.endif\n' in block
               for block in blocks), \
        'Darwin target LDFLAGS override is missing'
    # GNU iconv.h in ${LOCALBASE}/include renames iconv_open to libiconv_open.
    for name in ('CFLAGS', 'CXXFLAGS'):
        line = ('+CONFIGURE_ENV+=\t' + name + '_FOR_TARGET=-g\\ ${' + name +
                ':N-I${LOCALBASE}*:N-I${BUILDLINK_DIR}*:Q}\n')
        assert any(line in block for block in blocks), 'Darwin target ' + name + ' keep ${LOCALBASE}/include'
    assert ('-CONFIGURE_ENV+=\t\tLDFLAGS_FOR_TARGET=${LDFLAGS_FOR_TARGET:Q}\n'
            '+CONFIGURE_ENV+=\t\tLDFLAGS_FOR_TARGET=${GCC16_TARGET_LDFLAGS:Q}\n') in recipe, \
        'configure does not receive the Darwin target LDFLAGS'
    patch = (root / 'profiles/development-toolchain/patches/gcc-darwin-libstdcxx-iconv.patch').read_text()
    assert '+++ libstdc++-v3/src/c++20/format.cc\n' in patch
    block = re.search(r'#  include <iconv.h>\n.*?\n # endif\n', patch, re.S)
    assert block, 'linker option is not inside the iconv block'
    assert '+#  ifdef __APPLE__\n+' in block.group(0)
    assert '+__asm__ (".linker_option \\"-liconv\\"");\n' in block.group(0)
    export = (root / 'pkgsrc/export.conf').read_text()
    assert ('recipe-patch\tprofiles/development-toolchain/patches/gcc-darwin-libstdcxx-iconv.patch\t'
            'lang/gcc16\tpatch-libstdc++-v3_src_c++20_format_darwin_iconv\n') in export


def load_commands(objdump, path):
    text = subprocess.run([objdump, '--macho', '--private-headers', str(path)],
                          check=True, capture_output=True, text=True).stdout
    dylibs = re.findall(r'cmd LC_LOAD(?:_WEAK)?_DYLIB\n\s+cmdsize \d+\n\s+name (\S+)', text)
    rpaths = re.findall(r'cmd LC_RPATH\n\s+cmdsize \d+\n\s+path (\S+)', text)
    return dylibs, rpaths


def check_link(cxx, objdump, work):
    work.mkdir()
    (work / 'format.cc').write_text(PROGRAM)
    out = work / 'format'
    # No -liconv and no library path: the runtime must carry its dependency.
    link = subprocess.run([*shlex.split(cxx), '-std=c++23', '-O2', '-static-libstdc++', '-static-libgcc',
                           str(work / 'format.cc'), '-o', str(out)], capture_output=True, text=True)
    undefined = sorted(set(re.findall(r'undefined symbol: (\S+)', link.stderr)))
    assert link.returncode == 0, 'static link failed: ' + (', '.join(undefined) or link.stderr[-2000:])
    assert subprocess.run([str(out)]).returncode == 0, 'program returned a wrong result'
    dylibs, rpaths = load_commands(objdump, out)
    assert '/usr/lib/libiconv.2.dylib' in dylibs, dylibs
    assert all(name.startswith(('/usr/lib/', '/System/Library/')) for name in dylibs), dylibs
    assert not rpaths, rpaths


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--cxx', help='installed GCC16 C++ command, for example PREFIX/gcc16/bin/g++')
    parser.add_argument('--objdump', help='llvm-objdump path (required with --cxx)')
    parser.add_argument('--work', type=Path, help='new scratch directory (required with --cxx)')
    args = parser.parse_args()
    try:
        check_sources(args.root)
        if args.cxx:
            if not args.objdump or not args.work or args.work.exists():
                parser.error('--cxx needs --objdump and a new --work directory')
            check_link(args.cxx, args.objdump, args.work)
    except AssertionError as error:
        print('FAIL:', error)
        return 1
    print('PASS: Darwin libstdc++ uses the system iconv' +
          ('; -static-libstdc++ std::format link needs no extra library' if args.cxx else ' (sources)'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
