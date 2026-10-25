#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Build a library with the Darwin bootstrap mk files and a linker without -r.

Assemble share/mk from an exported pkgtools/bootstrap-mk-files the way its
do-configure target does, then build a one-object static library with bmake,
GCC and ld64.lld. The library rules must not run the linker on the object.
"""
import argparse
import os
import shutil
import subprocess
import tempfile

parser = argparse.ArgumentParser()
for name in ('pkgsrc', 'bmake', 'cc', 'ld', 'ar', 'ranlib', 'nm', 'work-parent'):
    parser.add_argument('--' + name, required=True)
a = parser.parse_args()
files = os.path.join(a.pkgsrc, 'pkgtools/bootstrap-mk-files/files')


def require(condition, message):
    if not condition:
        raise SystemExit('FAIL: ' + message)


with tempfile.TemporaryDirectory(prefix='mk-files-darwin-', dir=a.work_parent) as work:
    mk, src = os.path.join(work, 'mk'), os.path.join(work, 'src')
    shutil.copytree(files, mk)
    for name in os.listdir(mk):
        if name == 'sys.mk' or name.startswith('bsd.'):
            mod = os.path.join(mk, 'mods', 'Darwin.' + name)
            if os.path.isfile(mod):
                shutil.copyfile(mod, os.path.join(mk, name))
    own = os.path.join(mk, 'mods', 'Darwin.bsd.own.mk.in')
    own = own if os.path.isfile(own) else os.path.join(mk, 'mods', 'bsd.own.mk.in')
    text = open(own).read()
    for key, value in (('ROOT_GROUP', 'wheel'), ('ROOT_USER', 'root'), ('SYSCONFDIR', work)):
        text = text.replace('@' + key + '@', value)
    open(os.path.join(mk, 'bsd.own.mk'), 'w').write(text)
    os.mkdir(src)
    open(os.path.join(src, 'probe.c'), 'w').write('int ember_probe(void) { return 42; }\n')
    open(os.path.join(src, 'Makefile'), 'w').write(
        'LIB=\tprobe\nSRCS=\tprobe.c\nMKPROFILE=\tno\nMKPIC=\tno\nMKLINT=\tno\n'
        'MKMAN=\tno\nNOPROFILE=\tyes\nNOPIC=\tyes\nNOLINT=\tyes\n.include <bsd.lib.mk>\n')
    result = subprocess.run(
        [a.bmake, '-m', mk, 'MAKECONF=/dev/null', 'MAKEOBJDIRPREFIX=', 'CC=' + a.cc, 'LD=' + a.ld,
         'AR=' + a.ar, 'RANLIB=' + a.ranlib, 'NM=' + a.nm, 'LORDER=echo', 'TSORT=cat', 'all'],
        cwd=src, env={'PATH': '/usr/bin:/bin', 'HOME': work}, capture_output=True, text=True)
    output = result.stdout + result.stderr
    require(result.returncode == 0, 'library build failed:\n' + output[-2000:])
    archive = os.path.join(src, 'libprobe.a')
    require(os.path.isfile(archive), 'libprobe.a is missing')
    symbols = subprocess.run([a.nm, archive], capture_output=True, text=True, check=True).stdout
    require('_ember_probe' in symbols, 'libprobe.a lacks the probe symbol:\n' + symbols)
    require(not os.path.exists(os.path.join(src, 'probe.o.o')), 'temporary object was left behind')
print('PASS')
