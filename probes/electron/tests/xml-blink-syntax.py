#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Compile actual configured Blink XSLT sources with selected common headers."""
import argparse
import os
from pathlib import Path
import re
import shlex
import subprocess

p=argparse.ArgumentParser(description=__doc__)
for name in ('out','sysroot','host-prefix'): p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args(); out=a.out.resolve(strict=True); sysroot=a.sysroot.resolve(strict=True)
lines=(out/'obj/third_party/blink/renderer/core/core.ninja').read_text().splitlines()
variables={}
for line in lines[:8]:
    if ' = ' in line:
        key,value=line.split(' = ',1); variables[key]=shlex.split(value)
flags=[]; removed=[]
for key in ('defines','include_dirs','cflags','cflags_cc'):
    for value in variables[key]:
        if value.startswith('-I') and any(part in value for part in
                ('third_party/libxml/src/include','third_party/libxml/linux/include','third_party/libxslt/src')):
            removed.append(value)
        else:
            flags.append(value)
if len(removed) < 3:
    raise SystemExit('expected configured bundled XML and XSLT include paths')
flags[0:0]=['-I'+str(sysroot/'usr/pkg/include/libxml2'), '-I'+str(sysroot/'usr/pkg/include')]
rules=(out/'toolchain.ninja').read_text()
match=re.search(r'^rule cxx\n  command =\s+(\S+)',rules,re.M)
if not match:
    raise SystemExit('configured target C++ command unavailable')
compiler=Path(match.group(1)).resolve(strict=True)
environment=dict(os.environ, PATH=str(a.host_prefix.resolve(strict=True)/'bin'))
for name in ('xslt_extensions.cc','xslt_processor_libxslt.cc','xslt_unicode_sort.cc',
             'xsl_style_sheet_libxslt.cc'):
    source='../source-view/src/third_party/blink/renderer/core/xml/'+name
    subprocess.run([str(compiler),*flags,'-fsyntax-only',source],cwd=out,env=environment,check=True)
    print('PASS:',name,flush=True)
