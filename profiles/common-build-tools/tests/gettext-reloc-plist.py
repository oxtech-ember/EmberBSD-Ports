#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Package gettext's relocatable program.bin payloads.

The NetBSD cross file check for gettext-tools-1.0nb9 reported 25 staged
files absent from the PLIST. install-reloc had renamed each real program
to program.bin and left the relocating wrapper at the public name. The
public names were already listed. The four names at the end of that report
are the same omission as the other 21, not a separate set. Scripts have
no .bin sibling. Darwin does not install program.bin, so the entries are
conditional. This checks that packaging both ways, then runs the real
install-reloc script and executes the wrapper it installs.
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile

PORTS = Path(__file__).resolve().parents[3]
PATCH = PORTS / 'profiles/common-build-tools/patches/pkgsrc-gettext-reloc-bins.patch'
REVISION = PORTS / 'profiles/common-build-tools/patches/pkgsrc-gettext-external-tree-sitter.patch'
RECIPE = PORTS / 'profiles/common-build-tools/patches/gettext-external-recipe.patch'
EXPORT = PORTS / 'pkgsrc/export.conf'
MAC_EXTRAS = (
    'bin/envsubst.bin', 'bin/gettext.bin', 'bin/msgattrib.bin', 'bin/msgcat.bin',
    'bin/msgcmp.bin', 'bin/msgcomm.bin', 'bin/msgconv.bin', 'bin/msgen.bin',
    'bin/msgexec.bin', 'bin/msgfilter.bin', 'bin/msgfmt.bin', 'bin/msggrep.bin',
    'bin/msginit.bin', 'bin/msgmerge.bin', 'bin/msgpre.bin', 'bin/msgunfmt.bin',
    'bin/msguniq.bin', 'bin/ngettext.bin', 'bin/printf_gettext.bin',
    'bin/printf_ngettext.bin', 'bin/recode-sr-latin.bin', 'bin/xgettext.bin',
    'libexec/gettext/cldr-plurals.bin', 'libexec/gettext/hostname.bin',
    'libexec/gettext/urlget.bin')
SCRIPTS = (
    'bin/autopoint', 'bin/gettext.sh', 'bin/gettextize', 'bin/po-fetch', 'bin/spit',
    'libexec/gettext/project-id', 'libexec/gettext/user-email')


def fail(message):
    print('FAIL: ' + message, file=sys.stderr)
    raise SystemExit(1)


def require(condition, message):
    if not condition:
        fail(message)


def run(args, **kwargs):
    return subprocess.run(args, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, **kwargs)


def files_from_patch(text, side):
    """Rebuild one side of a unified diff, hunks concatenated."""
    result = {}
    name = None
    lines = []

    def finish():
        if name is not None:
            result[name] = ''.join(lines)

    for line in text.splitlines(True):
        if line.startswith('--- a/'):
            finish()
            name = line[6:].split('\t', 1)[0].strip()
            lines = []
            continue
        if name is None or line.startswith(('+++ ', '@@', 'diff ')):
            continue
        marker = line[0]
        if marker == '\\':
            continue
        keep = marker in (' ', '-') if side == 'before' else marker in (' ', '+')
        if keep:
            lines.append(line[1:])
    finish()
    return result


def active(plist, relocbin):
    names = []
    prefix = '${PLIST.relocbin}'
    for line in plist.splitlines():
        if line.startswith(prefix):
            if relocbin:
                names.append(line[len(prefix):])
            continue
        if not line or line.startswith('@') or line.startswith('${PLIST.'):
            continue
        names.append(line)
    return names


def classify(listed, staged):
    listed = set(listed)
    staged = set(staged)
    return sorted(staged - listed), sorted(listed - staged)


def apply_patch(patch_bin, patch, root):
    result = run([patch_bin, '-f', '-E', '-d', str(root), '-p1', '-F', '0', '-V', 'none'],
                 input=patch.read_text())
    require(result.returncode == 0,
            'reloc bin patch did not apply\n' + result.stdout + result.stderr)


def check_packaging(patch_bin):
    patch = PATCH.read_text()
    added = tuple(line[len('+${PLIST.relocbin}'):].strip()
                  for line in patch.splitlines() if line.startswith('+${PLIST.relocbin}'))
    require(added == MAC_EXTRAS, 'patch does not list the 25 Mac extras: ' + ' '.join(added))
    for script in SCRIPTS:
        require(script + '.bin' not in patch, 'script gained a .bin entry: ' + script)
    before = files_from_patch(patch, 'before')
    require(set(before) == {'devel/gettext-tools/Makefile', 'devel/gettext-tools/PLIST'},
            'patch does not edit the tools Makefile and PLIST')
    pre_extras, pre_missing = classify(active(before['devel/gettext-tools/PLIST'], False),
                                       active(before['devel/gettext-tools/PLIST'], False) + list(MAC_EXTRAS))
    require(pre_extras == list(MAC_EXTRAS) and pre_missing == [],
            'pre-patch file check was not the 25 extras: ' + ' '.join(pre_extras + pre_missing))
    print('PRE-FAIL: 25 program.bin extras, scripts not included')
    with tempfile.TemporaryDirectory(prefix='gettext-plist-') as temporary:
        root = Path(temporary)
        for relative, text in before.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        apply_patch(patch_bin, PATCH, root)
        plist = (root / 'devel/gettext-tools/PLIST').read_text()
        makefile = (root / 'devel/gettext-tools/Makefile').read_text()
    require('.if ${OPSYS} == "NetBSD" && ${USE_CROSS_COMPILE:Uno:tl} == "yes"\n'
            'PLIST.relocbin=\tyes\n' in makefile,
            'NetBSD cross condition does not select program.bin')
    cross_listed = active(plist, True)
    darwin_listed = active(plist, False)
    cross_extras, cross_missing = classify(cross_listed,
                                           active(before['devel/gettext-tools/PLIST'], False) + list(MAC_EXTRAS))
    darwin_staged = active(before['devel/gettext-tools/PLIST'], False)
    darwin_extras, darwin_missing = classify(darwin_listed, darwin_staged)
    require(cross_extras == [] and cross_missing == [],
            'cross file check failed: extras ' + ' '.join(cross_extras)
            + ' missing ' + ' '.join(cross_missing))
    require(darwin_extras == [] and darwin_missing == [],
            'Darwin file check failed: extras ' + ' '.join(darwin_extras)
            + ' missing ' + ' '.join(darwin_missing))
    require(not any(name.endswith('.bin') for name in darwin_listed),
            'Darwin PLIST requires program.bin')
    print('POST-PASS: cross lists 25 program.bin payloads; Darwin does not')


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
    require(sources[0] == 'relocwrapper.c', 'install-reloc wrapper is not relocwrapper.c')
    require('access.c' not in sources, 'install-reloc wrapper list gained access.c')
    return sources


def execute_payload(archive, output, compiler):
    source_root = output / 'source'
    with tarfile.open(archive) as packed:
        wanted = {
            'gettext-1.0/build-aux/install-reloc',
            'gettext-1.0/gettext-tools/gnulib-lib/relocwrapper.c',
            'gettext-1.0/gettext-tools/gnulib-lib/progname.h',
            'gettext-1.0/gettext-tools/gnulib-lib/relocatable.h',
            'gettext-1.0/gettext-tools/gnulib-lib/c-ctype.h',
            'gettext-1.0/gettext-tools/gnulib-lib/arg-nonnull.h'}
        members = [member for member in packed.getmembers() if member.name in wanted]
        require(len(members) == len(wanted), 'gettext archive is missing relocwrapper sources')
        packed.extractall(source_root, members=members, filter='data')
    tree = source_root / 'gettext-1.0'
    script = tree / 'build-aux/install-reloc'
    srcdir = output / 'srcdir'
    srcdir.mkdir()
    (srcdir / 'malloc').mkdir()
    gnulib = tree / 'gettext-tools/gnulib-lib'
    for name in ('relocwrapper.c', 'progname.h', 'relocatable.h', 'c-ctype.h', 'arg-nonnull.h'):
        shutil.copy(gnulib / name, srcdir / name)
    stub = (
        'const char *program_name;\n'
        'void set_program_name_and_installdir(const char *name, const char *prefix,\n'
        '                                     const char *dir) {\n'
        '  (void)prefix; (void)dir;\n'
        '  program_name = name;\n'
        '}\n'
        'char *get_full_program_name(void) { return 0; }\n'
        'const char *relocate(const char *path) { return path; }\n')
    for name in wrapper_sources(script.read_text()):
        if name == 'relocwrapper.c':
            continue
        path = srcdir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(stub if name == 'progreloc.c' else '\n')
    config = output / 'config'
    config.mkdir()
    config.joinpath('config.h').write_text(
        '#define _GL_CONFIG_H_INCLUDED 1\n'
        '#define ENABLE_RELOCATABLE 1\n'
        '#define DLL_VARIABLE\n'
        '#define HAVE_VISIBILITY 0\n'
        '#define _GL_INLINE static inline\n'
        '#define _GL_INLINE_HEADER_BEGIN\n'
        '#define _GL_INLINE_HEADER_END\n'
        '#define _GL_ATTRIBUTE_MALLOC\n'
        '#define _GL_ATTRIBUTE_DEALLOC_FREE\n'
        '#include <assert.h>\n'
        '#include <stdbool.h>\n')
    payload_source = output / 'payload.c'
    payload_source.write_text(
        '#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\n'
        'int main(int argc, char **argv) {\n'
        '  const char *libs = getenv("LD_LIBRARY_PATH");\n'
        '  if (argc != 2 || strcmp(argv[1], "marker") != 0) return 2;\n'
        '  if (libs == NULL || strstr(libs, "/usr/pkg/lib") == NULL) return 3;\n'
        '  if (strstr(argv[0], ".bin") == NULL) return 4;\n'
        '  printf("payload:%s\\nlibs:%s\\n", argv[0], libs);\n'
        '  return 0;\n'
        '}\n')
    payload = output / 'payload'
    compiled = run([compiler, '-o', str(payload), str(payload_source)])
    require(compiled.returncode == 0, 'payload compile failed\n' + compiled.stderr)
    stage = output / 'stage'
    environment = os.environ.copy()
    environment.update({
        'RELOC_LIBRARY_PATH_VAR': 'LD_LIBRARY_PATH',
        'RELOC_LIBRARY_PATH_VALUE': '/usr/pkg/lib',
        'RELOC_PREFIX': '/usr/pkg',
        'RELOC_DESTDIR': str(stage),
        'RELOC_COMPILE_COMMAND': compiler + ' -std=gnu17',
        'RELOC_SRCDIR': str(srcdir),
        'RELOC_BUILDDIR': str(config),
        'RELOC_CONFIG_H_DIR': str(config),
        'RELOC_EXEEXT': '',
        'RELOC_STRIP_PROG': ':',
        'RELOC_INSTALL_PROG': 'install -c -m 755'})
    for relative in ('usr/pkg/bin/xgettext', 'usr/pkg/libexec/gettext/hostname'):
        destination = stage / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        installed = run([str(script), str(payload), str(destination)],
                        cwd=output, env=environment)
        require(installed.returncode == 0,
                'install-reloc failed for ' + relative + '\n'
                + installed.stdout + installed.stderr)
        require(destination.is_file() and Path(str(destination) + '.bin').is_file(),
                'install-reloc did not stage wrapper and program.bin for ' + relative)
        executed = run([str(destination), 'marker'])
        require(executed.returncode == 0 and executed.stdout.startswith('payload:'),
                'wrapper did not execute program.bin for ' + relative + '\n'
                + executed.stdout + executed.stderr)
        require(executed.stdout.splitlines()[0].endswith('.bin'),
                'wrapper executed a program that is not program.bin\n' + executed.stdout)
        print('PAYLOAD: ' + relative + ' -> ' + executed.stdout.splitlines()[0])


def main():
    if len(sys.argv) != 3:
        fail('Usage: gettext-reloc-plist.py ARCHIVE NEW_OUTPUT')
    archive = Path(sys.argv[1]).resolve()
    output = Path(sys.argv[2])
    require(archive.is_file(), 'gettext archive is missing')
    require(output.is_absolute() and not output.exists(),
            'output must be a new absolute directory')
    require(archive.name in ('gettext-1.0.tar.gz', 'gettext-1.0.tar.xz'),
            'archive must be the gettext 1.0 tarball')
    for path in (PATCH, REVISION, RECIPE, EXPORT):
        require(path.is_file(), 'missing ' + str(path))
    patch_bin = shutil.which('gpatch') or shutil.which('patch')
    compiler = shutil.which('cc')
    require(patch_bin and compiler and shutil.which('install'),
            'patch, cc, and install are required')
    revision = REVISION.read_text()
    require('+PKGREVISION=\t10\n' in revision, 'shared gettext-tools revision is not 10')
    require('+PKGREVISION=\t9\n' not in revision, 'shared gettext-tools revision is still 9')
    require('+PKGREVISION= 9\n' in revision, 'Darwin gettext-tools revision is not 9')
    require('--enable-relocatable' in RECIPE.read_text(), 'relocatable gettext-tools was removed')
    export = EXPORT.read_text().splitlines()
    recipe = next(index for index, line in enumerate(export)
                  if line == 'patch\tprofiles/common-build-tools/patches/gettext-external-recipe.patch')
    reloc = next(index for index, line in enumerate(export)
                 if line == 'patch\tprofiles/common-build-tools/patches/pkgsrc-gettext-reloc-bins.patch')
    require(reloc == recipe + 3, 'program.bin patch is not immediately after the style PLIST patch')
    output.mkdir()
    check_packaging(patch_bin)
    execute_payload(archive, output, compiler)
    print('PASS: gettext-tools packages program.bin on NetBSD cross and runs the wrapper')


if __name__ == '__main__':
    main()
