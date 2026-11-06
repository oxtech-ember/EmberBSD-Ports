#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Compile the actual draft Xt lexer and common private helper, no X server."""
import argparse,pathlib,platform,subprocess,tempfile
p=argparse.ArgumentParser()
for x in ('cc','xt-source','x11-header'):p.add_argument('--'+x,required=True)
a=p.parse_args()
if platform.system()!='Darwin':raise SystemExit('Darwin-only fixture')
source=pathlib.Path(a.xt_source).read_text(); start=source.index('static char *\nimplementation_relocated_path');end=source.index('\n\n/* *INDENT-OFF* */',start); lexer=source[start:end]
with tempfile.TemporaryDirectory(prefix='xt-template-') as tmp:
 root=pathlib.Path(tmp);lib=root/'lib';lib.mkdir();header=pathlib.Path(a.x11_header);(root/'XlibRelocate.h').symlink_to(header.resolve())
 (root/'lib.c').write_text('#include <stdint.h>\n#define X11_RELOC_PREFIX "/original/sdk"\n#define X11_RELOC_LIBDIR "/original/sdk/lib"\n#include "XlibRelocate.h"\nstatic const char xt_relocation_anchor;\n'+lexer+'\nchar *probe(const char *x) { return implementation_relocated_path(x); }\n')
 def run(args):
  result=subprocess.run(args,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30)
  if result.returncode:raise SystemExit(result.stdout)
  return result.stdout
 dylib=lib/'libXt.6.dylib';fixture=pathlib.Path(__file__).resolve().parent/'xt-template-fixture.c'
 run([a.cc,'-DX11_RELOC_HAVE_DLADDR','-I'+str(root),'-dynamiclib',str(root/'lib.c'),'-Wl,-install_name,@rpath/libXt.6.dylib','-o',str(dylib)])
 run([a.cc,str(fixture),str(dylib),'-Wl,-rpath,'+str(lib),'-o',str(root/'test')])
 print(run([str(root/'test'),str(root.resolve())]).strip())
