#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise real gpg-error paths and allocator in a disposable moved SDK."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile
import uuid

p = argparse.ArgumentParser(description=__doc__)
for name in ('prefix', 'cc', 'work'):
    p.add_argument('--' + name, type=Path, required=True)
p.add_argument('--expect', choices=('old', 'new'), required=True)
a = p.parse_args()
for value in (a.prefix, a.cc, a.work):
    if not value.is_absolute():
        p.error('paths must be absolute')
if os.uname().sysname != 'Darwin':
    p.error('Darwin runtime is required')
env = dict(os.environ)
for name in list(env):
    if name.startswith('DYLD_'):
        del env[name]
source = r'''
#include <gpg-error.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
extern char *libintl_bindtextdomain(const char *, const char *);
static int allocations, frees;
static void *tracked(void *p, size_t n) {
  if (!n) { if (p) frees++; free(p); return NULL; }
  if (!p) allocations++;
  return realloc(p,n);
}
int main(int argc, char **argv) {
  char *path; const char *locale; int failures = 0;
  if (argc != 3 || !gpgrt_check_version(NULL)) return 2;
  locale = libintl_bindtextdomain("libgpg-error", NULL);
  if (!locale || strcmp(locale, argv[2])) failures |= 1;
  gpgrt_set_alloc_func(tracked);
  path = gpgrt_fconcat(GPGRT_FCONCAT_SYSCONF, "/ember-probe", NULL);
  if (!path) return 4;
  if (strcmp(path, argv[1])) failures |= 2;
  gpgrt_free(path);
  return !allocations || !frees ? 6 : failures;
}
'''
a.work.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(prefix='gpg-relocation-', dir=a.work) as temp:
    work = Path(temp)
    (work / 'probe.c').write_text(source)
    subprocess.run([str(a.cc), '-Wall', '-Wextra', '-Werror',
                    '-I' + str(a.prefix / 'include'), str(work / 'probe.c'),
                    '-L' + str(a.prefix / 'lib'), '-lgpg-error', '-lintl',
                    '-Wl,-rpath,' + str(a.prefix / 'lib'), '-o', str(work / 'probe')],
                   check=True, env=env)
    result = subprocess.run([str(work / 'probe'), str(a.prefix / 'lib/../etc/ember-probe'),
                             str(a.prefix / 'lib/../share/locale')], env=env)
    assert result.returncode == (0 if a.expect == 'new' else 3), result.returncode
    ref = a.prefix / 'share/libgpg-error/errorref.txt'
    assert ref.is_file() and not ref.is_symlink()
    old = ref.read_bytes()
    old_mode = ref.stat().st_mode & 0o7777
    marker = 'EMBER_RELOC_' + uuid.uuid4().hex
    try:
        ref.write_text('GPG_ERR_GENERAL General error\n    ' + marker + '\n')
        command = [str(a.prefix / 'bin/gpg-error'), '-d', 'GPG_ERR_GENERAL']
        found = subprocess.run(command, env=env, capture_output=True, text=True, check=True)
        assert (marker in found.stdout) == (a.expect == 'new')
        if a.expect == 'new':
            ref.unlink()
            missing = subprocess.run(command, env=env, capture_output=True, text=True)
            assert missing.returncode == 0 and 'cannot open relocated error reference' in missing.stderr
    finally:
        ref.write_bytes(old)
        ref.chmod(old_mode)
print('PASS ' + a.expect + ' moved sysconf, locale and errorref behavior')
