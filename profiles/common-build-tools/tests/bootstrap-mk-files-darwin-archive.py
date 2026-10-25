#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted). Uses the recipe's own configure phase.
"""Build a static library with the configured Darwin bootstrap mk files.

Run the configure phase of an exported pkgtools/bootstrap-mk-files with
EMBERBSD_DARWIN_BOOTSTRAP=yes, then build a two-object library with bmake
and those mk files. As in the native bootstrap, PATH has cat, echo and the
usual file tools, but not lorder(1) or tsort(1). The archive must contain
both objects, and a program that calls into the first object, which calls
the second, must link and run.
"""
import argparse
import os
import subprocess
import tempfile

parser = argparse.ArgumentParser()
for name in ('pkgsrc', 'bmake', 'makeconf', 'cc', 'ar', 'ranlib', 'nm', 'work-parent'):
    parser.add_argument('--' + name, required=True)
a = parser.parse_args()


def require(condition, message):
    if not condition:
        raise SystemExit('FAIL: ' + message)


def run(argv, **kwargs):
    return subprocess.run(argv, capture_output=True, text=True, **kwargs)


with tempfile.TemporaryDirectory(prefix='mk-files-archive-', dir=os.path.realpath(a.work_parent)) as work:
    recipe = os.path.join(a.pkgsrc, 'pkgtools/bootstrap-mk-files')
    base = {'PATH': '/usr/bin:/bin', 'HOME': work}
    configure = [a.bmake, '-C', recipe, 'EMBERBSD_DARWIN_BOOTSTRAP=yes', 'MAKECONF=' + a.makeconf,
                 'WRKOBJDIR=' + os.path.join(work, 'obj')]
    result = run(configure + ['configure'], env=base)
    require(result.returncode == 0, 'configure failed:\n' + (result.stdout + result.stderr)[-2000:])
    mk = run(configure + ['show-var', 'VARNAME=WRKSRC'], env=base, check=True).stdout.strip()
    bindir, src = os.path.join(work, 'bin'), os.path.join(work, 'src')
    os.mkdir(bindir)
    # The pkgsrc tool PATH has the usual file tools, but no lorder or tsort.
    for tool in ('cat', 'cp', 'echo', 'ln', 'mkdir', 'mv', 'rm', 'sed', 'touch'):
        target = next(p for p in ('/bin/' + tool, '/usr/bin/' + tool) if os.path.exists(p))
        os.symlink(target, os.path.join(bindir, tool))
    os.mkdir(src)
    open(os.path.join(src, 'first.c'), 'w').write(
        'int ember_second(void);\nint ember_first(void) { return ember_second() + 1; }\n')
    open(os.path.join(src, 'second.c'), 'w').write('int ember_second(void) { return 41; }\n')
    open(os.path.join(src, 'main.c'), 'w').write(
        'int ember_first(void);\nint main(void) { return ember_first() == 42 ? 0 : 1; }\n')
    open(os.path.join(src, 'Makefile'), 'w').write(
        'LIB=\tprobe\nSRCS=\tfirst.c second.c\nMKPROFILE=\tno\nMKPIC=\tno\nMKLINT=\tno\n'
        'MKMAN=\tno\nNOPROFILE=\tyes\nNOPIC=\tyes\nNOLINT=\tyes\n.include <bsd.lib.mk>\n')
    result = run([a.bmake, '-m', mk, 'MAKECONF=/dev/null', 'MAKEOBJDIRPREFIX=', 'CC=' + a.cc,
                  'AR=' + a.ar, 'RANLIB=' + a.ranlib, 'NM=' + a.nm, 'all'],
                 cwd=src, env={'PATH': bindir, 'HOME': work})
    output = result.stdout + result.stderr
    require(result.returncode == 0 and 'lorder' not in output, 'library build failed:\n' + output[-2000:])
    members = run([a.ar, 't', os.path.join(src, 'libprobe.a')], check=True).stdout.split()
    require(sorted(members) == ['first.o', 'second.o'], f'libprobe.a members are {members}')
    program = os.path.join(src, 'probe')
    linked = run([a.cc, '-o', program, os.path.join(src, 'main.c'), '-L' + src, '-lprobe'], env=base)
    require(linked.returncode == 0, 'link failed:\n' + linked.stdout + linked.stderr)
    require(run([program]).returncode == 0, 'the linked program returned an error')
print('PASS')
