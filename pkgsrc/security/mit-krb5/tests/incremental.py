#!/usr/bin/env python3
"""Exercise actual lib.in/libnover.in + libobj.in with selected native tools."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

p = argparse.ArgumentParser()
p.add_argument('--source', type=Path, required=True)
p.add_argument('--cc', type=Path, required=True)
p.add_argument('--make', type=Path, required=True)
p.add_argument('--shell', type=Path, required=True)
p.add_argument('--tool-bin', type=Path, action='append', required=True)
p.add_argument('--work', type=Path, required=True)
a = p.parse_args()
if sys.platform != 'darwin':
    p.error('this native dynamic-library fixture currently supports Darwin')
if any(not x.is_absolute() or not x.is_file() for x in (a.cc, a.make, a.shell)):
    p.error('supply absolute selected SDK compiler, GNU make and shell paths')
if any(not x.is_absolute() or not x.is_dir() for x in a.tool_bin):
    p.error('each tool-bin must be an absolute selected tool directory')
env = dict(os.environ)
env['PATH'] = os.pathsep.join(str(x) for x in a.tool_bin)

def run(args, cwd):
    return subprocess.run([str(x) for x in args], cwd=cwd, text=True,
                          capture_output=True, check=True, timeout=60, env=env)

for kind in ('lib.in', 'libnover.in'):
    root = a.work / kind.replace('.', '-')
    child = root / 'child'
    child.mkdir(parents=True, exist_ok=True)
    (root / 'out').mkdir(exist_ok=True)
    source = (a.source / 'config' / kind).read_text()
    marker = '\t@: $@ updated by recursion\n'
    if source.count(marker) != 1:
        raise SystemExit('source does not have expected restat rule: ' + kind)
    frag = root / 'rules.in'
    tool = root / 'mini-libtool'
    tool.write_text('#!' + str(a.shell) + '''
set -eu
case "$1" in
--mode=compile) shift; "$@" -o child.o; printf '%s\\n' child.o > child.lo;;
--mode=link) shift; cc=$1; shift; test "$1" = -o; out=$2; shift 2; "$cc" -dynamiclib -o "$out" "${1%.lo}.o";;
esac
''')
    tool.chmod(0o755)
    lib = 'out/libfixture.la' if kind == 'lib.in' else 'out/fixture.la'
    root_make = f'''top_srcdir={a.source}
STLIBEXT=.a
SHLIBVEXT=.1.0.dylib
SHLIBSEXT=.1.dylib
SHLIBEXT=.dylib
PFLIBEXT=.p.a
CC={a.cc}
SHELL={a.shell}
LIBTOOL={tool}
LIBBASE=fixture
LALIBEXT=.la
TOPLIBD=out
SUBDIROBJLISTS=child/OBJS.ST
STOBJLISTS=OBJS.ST $(SUBDIROBJLISTS)
LIBLINKS=$(TOPLIBD)/lib$(LIBBASE)$(LALIBEXT)
PLUGIN=$(LIBBASE)$(LALIBEXT)
PLUGINLINK=
LN_S=ln -s
RM=rm -f
.PHONY: all all-recurse
all: all-liblinks
all-recurse:
\t$(MAKE) -C child all
include {frag}
'''
    (root / 'Makefile').write_text(root_make)
    (child / 'Makefile').write_text(f'''top_srcdir={a.source}
CC={a.cc}
SHELL={a.shell}
LIBTOOL={tool}
STLIBOBJS=child.o
LALIBOBJS=child.lo
OBJLISTS=OBJS.LA
.PHONY: all
all: all-libobjs
include {a.source / 'config/libobj.in'}
''')
    (root / 'OBJS.LA').write_text('\n')
    c = child / 'child.c'
    probe = root / 'probe.c'
    probe.write_text('#include <dlfcn.h>\n#include <stdio.h>\nint main(int argc,char **argv){void *h=dlopen(argv[1],RTLD_NOW); int(*f)(void); if(!h)return 2; *(void **)(&f)=dlsym(h,"fixture"); if(!f)return 3; printf("%d\\n",f()); return argc<2;}\n')
    run([a.cc, probe, '-o', root / 'probe'], root)
    def make():
        return run([a.make, '-j2'], root).stdout
    def result():
        return run([root / 'probe', root / lib], root).stdout.strip()
    frag.write_text(source.replace(marker, '', 1))
    c.write_text('int fixture(void) { return 1; }\n')
    make()
    c.write_text('int fixture(void) { return 2; }\n')
    make()
    if result() != '1':
        raise SystemExit(kind + ': old rule did not reproduce stale object')
    frag.write_text(source)
    make()
    c.write_text('int fixture(void) { return 3; }\n')
    log = make()
    if result() != '3' or 'building fixture libtool archive' not in log:
        raise SystemExit(kind + ': updated input did not relink')
    noop = make()
    if '--mode=compile' in noop or 'building fixture libtool archive' in noop:
        raise SystemExit(kind + ': no-op unexpectedly rebuilt')
    print('PASS:', kind, 'old stale, fixed updated, no-op preserved')
