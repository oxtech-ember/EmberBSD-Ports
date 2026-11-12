#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Exercise actual pkgsrc native and target Ruby metadata before and after the patch."""
import argparse, os, subprocess, tempfile, tarfile
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
for n in ('pkgsrc','makeconf','bmake','patch','overlay','archive'):p.add_argument('--'+n,type=Path,required=True)
a=p.parse_args();env=dict(os.environ,MAKECONF=str(a.makeconf))
with tarfile.open(a.archive, 'r:xz') as archive:
 configure=archive.extractfile('ruby-4.0.9/configure').read().decode()
 ruby=archive.extractfile('ruby-4.0.9/ruby.c').read().decode()
 assert '--enable-load-relative' in configure and 'ac_cv_func_dladdr' in configure
 assert 'runtime_libruby_path' in ruby and 'dladdr(' in ruby and '#if defined LOAD_RELATIVE' in ruby
with tempfile.TemporaryDirectory(prefix='ruby-relocatable-') as tmp:
 root=Path(tmp);recipe=root/'lang/ruby40/Makefile';recipe.parent.mkdir(parents=True);recipe.write_bytes((a.pkgsrc/'lang/ruby40/Makefile').read_bytes())
 def query(mode):
  result=subprocess.run([str(a.bmake),'-C',str(a.pkgsrc/'lang/ruby40'),'-f',str(recipe),'USE_CROSS_COMPILE='+mode,'show-vars','VARNAMES=OPSYS PKGREVISION CONFIGURE_ARGS'],env=env,check=True,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  fields=result.stdout.splitlines();assert len(fields)==3,fields;return fields
 old_native=query('no');old_target=query('yes');assert old_native[0]=='Darwin' and old_target[0]=='NetBSD'
 assert '--enable-load-relative' not in old_native[2] and old_native[1]=='1'
 subprocess.run([str(a.patch),'-d',str(root),'-p1','-F0','-i',str(a.overlay)],check=True,stdout=subprocess.PIPE)
 native=query('no');target=query('yes')
 assert native[0]=='Darwin' and native[1]=='2' and '--enable-load-relative' in native[2],native
 assert target==old_target,(old_target,target)
 print('PASS: old native lacks relative loading; new Darwin nb2 enables it; target metadata unchanged')
