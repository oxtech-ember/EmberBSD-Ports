#!/usr/bin/env python3
"""Compile the actual POSIX resolver in absolute and static-anchor modes."""
import argparse
from pathlib import Path
import subprocess

p = argparse.ArgumentParser()
p.add_argument('--source', type=Path, required=True, help='patched GLib source root')
p.add_argument('--cc', type=Path, required=True)
p.add_argument('--sdk', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
s = (a.source / 'glib/ggettext.c').read_text()
start = s.index('#else /* !G_OS_WIN32 */') + len('#else /* !G_OS_WIN32 */')
end = s.index('#endif /* G_OS_WIN32 */', start)
header = '''#define _GNU_SOURCE 1
#include <glib.h>
#include <dlfcn.h>
#include <stdlib.h>
#include <string.h>
#define GLIB_LOCALE_DIR "/synthetic/absolute/locale"
#ifdef TEST_STATIC_ANCHOR
#define GLIB_HAVE_LOCALE_DLADDR 1
#define GLIB_LOCALE_RELATIVE_TO_LIBDIR "../share/locale"
#endif
'''
main = '''\nint main(void) { gchar *p = _glib_get_locale_dir(); int ok = strcmp(p, GLIB_LOCALE_DIR) == 0; g_free(p); return !ok; }\n'''
a.output.mkdir(parents=True, exist_ok=True)
source = a.output / 'actual-resolver.c'
source.write_text(header + s[start:end] + main)
for label, flags in (('absolute', []), ('static-anchor', ['-DTEST_STATIC_ANCHOR'])):
    binary = a.output / label
    subprocess.run([str(a.cc), '-std=c11', *flags, '-I' + str(a.sdk / 'include/glib-2.0'),
                    '-I' + str(a.sdk / 'lib/glib-2.0/include'), str(source),
                    '-L' + str(a.sdk / 'lib'), '-Wl,-rpath,' + str(a.sdk / 'lib'),
                    '-lglib-2.0', '-o', str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
    print(label + ' PASS')
