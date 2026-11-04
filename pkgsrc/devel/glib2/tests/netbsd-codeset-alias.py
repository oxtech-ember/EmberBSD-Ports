#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted glib2 NetBSD codeset regression.
"""Build the GLib libcharset from the distfile and resolve NetBSD codeset names.

On NetBSD, nl_langinfo(CODESET) gives "646" in the C locale.  GNU libiconv
does not know this name and installs no charset.alias file.  The recipe
patch must give GNU canonical names without that file.  Other systems must
keep the upstream charset.alias lookup.
"""
import argparse
from pathlib import Path
import subprocess
import tarfile
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--cc', required=True, type=Path, help='a host C compiler')
parser.add_argument('--distfile', required=True, type=Path, help='glib-*.tar.xz')
parser.add_argument('--patch', default=Path('/usr/bin/patch'), type=Path)
parser.add_argument('--work-parent', required=True, type=Path)
a = parser.parse_args()
recipe = Path(__file__).resolve().parents[1]
names = ['646', 'ISO8859-1', 'eucJP', 'UTF-8']

DRIVER = r'''
#include <stdio.h>
#include "localcharset.h"
int
main(int argc, char **argv)
{
	for (int i = 1; i < argc; i++)
		printf("%s=%s\n", argv[i], _g_locale_charset_unalias(argv[i]));
	return 0;
}
'''

with tempfile.TemporaryDirectory(prefix='glib2-codeset-', dir=a.work_parent) as temporary:
    root = Path(temporary)
    with tarfile.open(a.distfile) as archive:
        for member in archive.getmembers():
            if member.name.endswith(('/glib/libcharset/localcharset.c',
                                     '/glib/libcharset/localcharset.h')):
                (root / Path(member.name).name).write_bytes(
                    archive.extractfile(member).read())
    (root / 'config.h').write_text('#define HAVE_LANGINFO_CODESET 1\n')
    (root / 'driver.c').write_text(DRIVER)
    # This file must be ignored on NetBSD and used on other systems.
    aliases = root / 'aliases'
    aliases.mkdir()
    (aliases / 'charset.alias').write_text('646 FROM-FILE\n')
    (root / 'upstream.c').write_bytes((root / 'localcharset.c').read_bytes())
    subprocess.run([str(a.patch), '-s', '-F0', 'localcharset.c',
                    str(recipe / 'patches/patch-glib_libcharset_localcharset.c')],
                   cwd=root, check=True)
    # Host headers must not see __NetBSD__ (GCC stddef.h then needs
    # <machine/ansi.h>).  Select the NetBSD branches with a test macro.
    for source in ('upstream.c', 'localcharset.c'):
        text = (root / source).read_text()
        (root / source).write_text(text.replace('__NetBSD__', 'GLIB2_TEST_NETBSD'))
    assert 'GLIB2_TEST_NETBSD' in (root / 'localcharset.c').read_text()

    def resolve(name, source, *defines):
        program = root / name
        subprocess.run([str(a.cc), '-std=c99', '-Wall', '-Werror', '-I', str(root),
                        f'-DGLIB_CHARSETALIAS_DIR="{aliases}"', *defines,
                        '-o', str(program), str(root / 'driver.c'), str(root / source)],
                       check=True)
        done = subprocess.run([str(program), *names], text=True, capture_output=True,
                              check=True)
        return dict(line.split('=', 1) for line in done.stdout.splitlines())

    # Prove the defect: upstream on NetBSD without charset.alias keeps "646".
    (aliases / 'charset.alias').rename(aliases / 'unused')
    result = resolve('upstream-netbsd', 'upstream.c', '-DGLIB2_TEST_NETBSD')
    assert result['646'] == '646', result
    (aliases / 'unused').rename(aliases / 'charset.alias')

    result = resolve('patched-netbsd', 'localcharset.c', '-DGLIB2_TEST_NETBSD')
    assert result == {'646': 'ASCII', 'ISO8859-1': 'ISO-8859-1', 'eucJP': 'EUC-JP',
                      'UTF-8': 'UTF-8'}, result

    result = resolve('patched-other', 'localcharset.c')
    assert result['646'] == 'FROM-FILE' and result['UTF-8'] == 'UTF-8', result
print('glib2 NetBSD codeset alias regression: ok')
