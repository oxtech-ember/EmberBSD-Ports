#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors, AI-assisted.
"""Exercise the real bsd.lib.mk archive install with selected LLVM tools."""
import argparse
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--host-prefix', required=True, type=Path)
parser.add_argument('--mk-dir', required=True, type=Path)
parser.add_argument('--work-parent', required=True, type=Path)
a = parser.parse_args()
prefix = a.host_prefix.resolve()
env = dict(os.environ, PATH=str(prefix/'bin')+':'+str(prefix/'sbin')+':'+str(prefix/'gnu/bin'))
def run(argv, cwd):
    result = subprocess.run([str(x) for x in argv], cwd=cwd, env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if result.returncode:
        raise SystemExit(result.stdout + '\nFAIL: ' + str(argv) + ' exit=' + str(result.returncode))
    return result.stdout
sources = [a.mk_dir/'bsd.lib.mk'] + sorted((a.mk_dir/'mods').glob('*.bsd.lib.mk'))
# Exercise the generic template and each override using ranlib during archive installation.
sources = [p for p in sources if '__archiveinstall:' in p.read_text() and
           '${RANLIB}' in p.read_text().split('__archiveinstall:', 1)[1].split('\n\n', 1)[0]]
assert sources, 'no archive-install templates selected'
for source in sources:
    with tempfile.TemporaryDirectory(prefix='archive-install-', dir=a.work_parent) as temp:
        work = Path(temp)
        mk = work/'mk'; mk.mkdir()
        shutil.copyfile(source, mk/'bsd.lib.mk')
        (work/'answer.c').write_text('int ember_answer(void) { return 42; }\n')
        (work/'main.c').write_text('int ember_answer(void);\nint main(void) { return ember_answer() == 42 ? 0 : 1; }\n')
        run([prefix/'bin/clang', '-c', 'answer.c', '-o', 'answer.o'], work)
        run([prefix/'bin/llvm-ar', 'rcS', 'libprobe.a', 'answer.o'], work)
        assert 'Archive map' not in run([prefix/'bin/llvm-nm', '--print-armap', 'libprobe.a'], work)
        dest = work/'dest'; dest.mkdir()
        (work/'Makefile').write_text('LIB=probe\nSRCS=\nMKPROFILE=no\nMKPIC=no\nMKLINT=no\nMKMAN=no\n.include <bsd.lib.mk>\n')
        command = [prefix/'bin/bmake','-m',mk,'-m',prefix/'share/mk',
                   'MAKECONF=/dev/null','LIBMODE=0644','LIBDIR='+str(dest),'LIBOWN='+str(os.getuid()),
                   'LIBGRP='+str(os.getgid()),'RANLIB='+str(prefix/'bin/llvm-ranlib'),
                   'AR='+str(prefix/'bin/llvm-ar'),'INSTALL='+str(prefix/'bin/ginstall'),'libinstall']
        run(command,work)
        installed = (dest/'libprobe.a').stat()
        assert stat.S_IMODE(installed.st_mode) == 0o644
        assert (installed.st_uid, installed.st_gid) == (os.getuid(), os.getgid())
        assert run([prefix/'bin/llvm-ar','t',dest/'libprobe.a'],work).split()==['answer.o']
        armap = run([prefix/'bin/llvm-nm', '--print-armap', dest/'libprobe.a'], work)
        assert 'Archive map' in armap and 'ember_answer in answer.o' in armap
        program=work/'consumer'
        run([prefix/'bin/clang','--ld-path='+str(prefix/'bin/ld.lld'),'main.c',dest/'libprobe.a','-o',program],work)
        run([program],work)
    print('PASS:', source)
print('PASS: archive installation, members, symbol lookup and execution for', len(sources), 'templates')
