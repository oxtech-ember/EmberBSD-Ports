#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Link gettext's relocating wrapper the way install-reloc does.

The NetBSD cross install of gettext-tools fails while building the msgcmp
wrapper: gnulib's unistd.h renames access to rpl_access, and install-reloc
compiles progreloc.c without access.c. This applies the recipe patch to
gettext 1.0 and repeats that compile and link. The host compiler is told
the target is NetBSD, so the Linux-only body stays out of the translation
unit the way it does for aarch64--netbsd-clang.
"""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile

PORTS = Path(__file__).resolve().parents[3]
PATCH = PORTS / 'profiles/common-build-tools/patches/gettext-reloc-wrapper-access.patch'
REVISION = PORTS / 'profiles/common-build-tools/patches/pkgsrc-gettext-external-tree-sitter.patch'
RECIPE = PORTS / 'profiles/common-build-tools/patches/gettext-external-recipe.patch'
EXPORT = PORTS / 'pkgsrc/export.conf'


def fail(message):
    print('FAIL: ' + message, file=sys.stderr)
    raise SystemExit(1)


def require(condition, message):
    if not condition:
        fail(message)


def run(args, **kwargs):
    result = subprocess.run(args, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, **kwargs)
    return result


def symbols(path):
    result = run(['nm', str(path)])
    require(result.returncode == 0, 'nm failed for ' + str(path) + '\n' + result.stderr)
    found = []
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        found.append((parts[-2], parts[-1].lstrip('_')))
    return found


def undefined(path):
    return {name for kind, name in symbols(path) if kind == 'U'}


def wrapper_sources(script):
    start = script.index('func_create_wrapper ()')
    chunk = script[start:script.index('rc=$?', start)]
    sources = []
    for line in chunk.splitlines():
        marker = '"$srcdir"/'
        if marker not in line:
            continue
        name = line.split(marker, 1)[1].strip().rstrip('\\').strip()
        require(name.endswith('.c'), 'install-reloc source is not a C file: ' + name)
        sources.append(name)
    require(sources, 'install-reloc published no wrapper sources')
    return sources, chunk


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    archive = args.archive.resolve()
    output = args.output
    require(archive.is_file(), 'gettext archive is missing')
    require(output.is_absolute(), 'output must be absolute')
    require(not output.exists(), 'output already exists')
    require(archive.name in ('gettext-1.0.tar.gz', 'gettext-1.0.tar.xz'),
            'archive must be the gettext 1.0 tarball')
    for path in (PATCH, REVISION, RECIPE, EXPORT):
        require(path.is_file(), 'missing ' + str(path))
    patch_bin = shutil.which('gpatch') or shutil.which('patch')
    compiler = shutil.which('cc')
    require(patch_bin and compiler and shutil.which('nm'),
            'patch, cc, and nm are required')
    revision = REVISION.read_text()
    require('+PKGREVISION=\t9\n' in revision, 'shared gettext-tools revision is not 9')
    require('+PKGREVISION= 9\n' in revision, 'Darwin gettext-tools revision is not 9')
    require('+PKGREVISION=\t8\n' not in revision, 'shared gettext-tools revision is still 8')
    require('--enable-relocatable' in RECIPE.read_text(), 'relocatable gettext-tools was removed')
    recipe_patch = PATCH.read_text()
    require('gl_cv_func_access_slash_works' not in recipe_patch,
            'wrapper patch overrides the access configure result')
    require('IN_RELOCWRAPPER' in recipe_patch and '# undef access' in recipe_patch,
            'wrapper patch does not keep the system access call')
    export = EXPORT.read_text().splitlines()
    selected = [line for line in export if line.startswith(
        'recipe-patch\tprofiles/common-build-tools/patches/gettext-reloc-wrapper-access.patch\t')]
    require(selected == [
        'recipe-patch\tprofiles/common-build-tools/patches/gettext-reloc-wrapper-access.patch\t'
        'devel/gettext\tpatch-zz_ember_reloc_wrapper_access'],
        'reloc wrapper patch is not exported onto devel/gettext')
    output.mkdir()
    with tempfile.TemporaryDirectory(prefix='gettext-reloc-', dir=output) as temporary:
        root = Path(temporary)
        with tarfile.open(archive) as packed:
            packed.extractall(root, filter='data')
        source = root / 'gettext-1.0'
        require((source / 'build-aux/install-reloc').is_file(), 'install-reloc is absent')
        originals = {}
        for relative in ('gettext-runtime/gnulib-lib/progreloc.c',
                         'gettext-tools/gnulib-lib/progreloc.c'):
            originals[relative] = (source / relative).read_bytes()
        applied = run([patch_bin, '-p0', '-f', '-N', '-F0', '-V', 'none',
                       '-i', str(PATCH)], cwd=source)
        (output / 'patch.log').write_text(applied.stdout + applied.stderr)
        require(applied.returncode == 0, 'reloc wrapper patch did not apply\n' + applied.stderr)
        script = (source / 'build-aux/install-reloc').read_text()
        sources, command = wrapper_sources(script)
        require('progreloc.c' in sources, 'install-reloc dropped progreloc.c')
        require('access.c' not in sources, 'install-reloc started compiling access.c')
        for token in ('-DHAVE_CONFIG_H', '-DIN_RELOCWRAPPER', '-DNO_XMALLOC',
                      '-D"EXEEXT=\\"$exeext\\""'):
            require(token in command, 'install-reloc lost ' + token)
        include = root / 'include'
        (include / 'sys').mkdir(parents=True)
        headers = {
            'config.h': '''
typedef int bool;
#define true 1
#define false 0
#define ENABLE_RELOCATABLE 1
#define memeq(a, b, n) (memcmp((a), (b), (n)) == 0)
''',
            'errno.h': 'extern int errno;\n',
            'stddef.h': 'typedef unsigned long size_t;\n#define NULL ((void *)0)\n',
            'stdio.h': 'typedef struct FILE FILE;\nextern FILE *stderr;\n',
            'stdlib.h': '''
#include <stddef.h>
void *malloc (size_t);
void free (void *);
char *getenv (const char *);
''',
            'string.h': '''
#include <stddef.h>
void *memcpy (void *, const void *, size_t);
int memcmp (const void *, const void *, size_t);
char *strcpy (char *, const char *);
size_t strlen (const char *);
char *strchr (const char *, int);
''',
            'fcntl.h': '''
#define O_RDONLY 0
#define O_EXEC 0
#define O_CLOEXEC 0
int open (const char *, int, ...);
''',
            'unistd.h': '''
#include <stddef.h>
#define X_OK 1
int access (const char *, int);
#undef access
#define access rpl_access
int rpl_access (const char *, int);
int getpid (void);
''',
            'sys/stat.h': '''
typedef unsigned long dev_t;
typedef unsigned long ino_t;
typedef unsigned int mode_t;
struct stat { dev_t st_dev; ino_t st_ino; mode_t st_mode; };
#define S_ISDIR(mode) ((mode) & 1)
int stat (const char *, struct stat *);
int fstat (int, struct stat *);
''',
            'progname.h': '''
extern const char *program_name;
extern void set_program_name (const char *argv0);
''',
            'relocatable.h': '''
extern char *compute_curr_prefix (const char *orig_installprefix,
    const char *orig_installdir, const char *curr_pathname);
extern void set_relocation_prefix (const char *orig_prefix, const char *curr_prefix);
''',
            'areadlink.h': '''
extern char *areadlink (const char *name);
#define xreadlink areadlink
''',
        }
        for name, text in headers.items():
            (include / name).write_text(text.lstrip('\n'))
        (root / 'stubs.c').write_text(r'''
#include <stddef.h>
const char *program_name;
void set_program_name (const char *argv0) { program_name = argv0; }
char *areadlink (const char *name) { (void) name; return 0; }
char *canonicalize_file_name (const char *name) { (void) name; return 0; }
char *compute_curr_prefix (const char *a, const char *b, const char *c) {
  (void) a; (void) b; (void) c; return 0;
}
void set_relocation_prefix (const char *a, const char *b) { (void) a; (void) b; }
int access (const char *file, int mode) { (void) file; (void) mode; return -1; }
void *malloc (size_t size) { (void) size; return 0; }
void free (void *pointer) { (void) pointer; }
void *memcpy (void *dest, const void *src, size_t size) {
  (void) src; (void) size; return dest;
}
int memcmp (const void *left, const void *right, size_t size) {
  (void) left; (void) right; (void) size; return 0;
}
char *strcpy (char *dest, const char *src) { (void) src; return dest; }
size_t strlen (const char *text) { (void) text; return 0; }
char *strchr (const char *text, int byte) { (void) text; (void) byte; return 0; }
char *getenv (const char *name) { (void) name; return 0; }
int stat (const char *path, void *state) { (void) path; (void) state; return -1; }
extern void set_program_name_and_installdir (const char *, const char *, const char *);
int main (void) {
  set_program_name_and_installdir ("msgcmp", "/usr/pkg", "/usr/pkg/bin");
  return 0;
}
''')
        flags = [compiler, '-std=gnu17', '-nostdinc', '-I', str(include),
                 '-DHAVE_CONFIG_H', '-DNO_XMALLOC', '-U__linux__', '-Ulinux',
                 '-D__NetBSD__', '-DINSTALLPREFIX="/usr/pkg"',
                 '-DINSTALLDIR="/usr/pkg/bin"', '-DLIBPATHVAR="LD_LIBRARY_PATH"',
                 '-DLIBDIRS="/usr/pkg/lib",', '-DEXEEXT=""', '-O2']
        tools_source = source / 'gettext-tools/gnulib-lib/progreloc.c'
        runtime_source = source / 'gettext-runtime/gnulib-lib/progreloc.c'
        for path in (tools_source, runtime_source):
            text = path.read_text()
            require('#if defined IN_RELOCWRAPPER\n' in text and '# undef access\n' in text,
                    path.name + ' wrapper still renames access')
            require('if (access (filename, X_OK) < 0)' in text,
                    'executable check was removed from ' + str(path))
        # Quote includes search the source directory first. Compile copies
        # away from gnulib's headers so the wrapper sees the renamed unistd.h
        # the same way -I../gnulib-lib does, without the neighboring headers
        # replacing the test's config.h guard.
        isolated = root / 'isolated'
        isolated.mkdir()
        tools = isolated / 'progreloc.c'
        runtime = isolated / 'progreloc-runtime.c'
        tools.write_bytes(tools_source.read_bytes())
        runtime.write_bytes(runtime_source.read_bytes())
        unpatched = isolated / 'progreloc-unpatched.c'
        unpatched.write_bytes(originals['gettext-tools/gnulib-lib/progreloc.c'])
        library = root / 'library.o'
        compiled = run(flags + ['-c', str(tools), '-o', str(library)])
        (output / 'library-compile.log').write_text(compiled.stderr)
        require(compiled.returncode == 0, 'library progreloc.c failed to compile\n' + compiled.stderr)
        require('rpl_access' in undefined(library),
                'library progreloc dropped the rpl_access dependency')
        wrapper = root / 'wrapper.o'
        compiled = run(flags + ['-DIN_RELOCWRAPPER', '-c', str(tools), '-o', str(wrapper)])
        (output / 'wrapper-compile.log').write_text(compiled.stderr)
        require(compiled.returncode == 0, 'wrapper progreloc.c failed to compile\n' + compiled.stderr)
        missing = undefined(wrapper)
        require('access' in missing and 'rpl_access' not in missing,
                'wrapper references ' + ' '.join(sorted(missing)))
        runtime_object = root / 'runtime-wrapper.o'
        compiled = run(flags + ['-DIN_RELOCWRAPPER', '-c', str(runtime), '-o', str(runtime_object)])
        require(compiled.returncode == 0, 'runtime wrapper progreloc.c failed to compile\n' + compiled.stderr)
        require('rpl_access' not in undefined(runtime_object),
                'runtime wrapper still references rpl_access')
        linked = run(flags + ['-DIN_RELOCWRAPPER', str(tools), str(root / 'stubs.c'),
                              '-o', str(output / 'msgcmp.wrapper')])
        (output / 'wrapper-link.log').write_text(linked.stderr)
        require(linked.returncode == 0, 'patched wrapper link failed\n' + linked.stderr)
        require('rpl_access' not in undefined(output / 'msgcmp.wrapper'),
                'linked wrapper still needs rpl_access')
        broken = run(flags + ['-DIN_RELOCWRAPPER', str(unpatched), str(root / 'stubs.c'),
                              '-o', str(root / 'msgcmp.broken')])
        (output / 'unpatched-link.log').write_text(broken.stderr)
        require(broken.returncode != 0 and 'rpl_access' in broken.stderr,
                'unpatched install-reloc link did not fail on rpl_access')
    print('PASS: gettext 1.0 install-reloc links the NetBSD wrapper without rpl_access')
    print('The library object still references rpl_access. This host cc is not aarch64--netbsd-ld.lld.')


if __name__ == '__main__':
    main()
