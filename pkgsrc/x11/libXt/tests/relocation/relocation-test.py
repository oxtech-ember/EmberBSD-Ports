#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Explicit Darwin native libX11/libXt no-X-server relocation regression."""
import argparse,os,pathlib,platform,shutil,subprocess,tempfile
p=argparse.ArgumentParser()
for opt in ('cc','host-prefix','old-x11','new-x11','old-xt','new-xt'):p.add_argument('--'+opt,required=True)
a=p.parse_args()
if platform.system()!='Darwin':raise SystemExit('Darwin-only fixture: uses DYLD loader tracing')
source=pathlib.Path(__file__).resolve().parent;prefix=pathlib.Path(a.host_prefix)
def run(cmd,env=None):return subprocess.run(cmd,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30)
with tempfile.TemporaryDirectory(prefix='x11-relocation-') as tmp:
 root=pathlib.Path(tmp);e=os.environ.copy()
 for k in ('DYLD_LIBRARY_PATH','XLOCALEDIR','XKEYSYMDB','XCMSDB'):e.pop(k,None)
 for role in ('old','new'):
  dest=root/role;(dest/'lib').mkdir(parents=True);(dest/'share/X11').mkdir(parents=True)
  shutil.copy2(getattr(a,role+'_x11'),dest/'lib/libX11.6.dylib');shutil.copy2(getattr(a,role+'_xt'),dest/'lib/libXt.6.dylib')
  (dest/'share/X11/XErrorDB').write_text('RelocProbe.Value: moved-message\n');(dest/'share/X11/XKeysymDB').write_text('RelocProbeUnique: 1234abcd\n');(dest/'share/X11/XtErrorDB').write_text('RelocProbe.Value: moved-xt-message\n')
  shutil.copytree(prefix/'share/X11/locale',dest/'share/X11/locale')
 for n,lib in [('probe','libX11.6.dylib'),('xt-probe','libXt.6.dylib')]:
  r=run([a.cc,'-I'+str(prefix/'include'),str(source/(n+'.c')),str(prefix/'lib'/lib),'-o',str(root/n)])
  if r.returncode:raise SystemExit('compile failed: '+r.stdout)
 for role in ('old','new'):
  env=e.copy();env['DYLD_LIBRARY_PATH']=str(root/role/'lib');env['DYLD_PRINT_LIBRARIES']='1'
  x=run([str(root/'probe')],env);t=run([str(root/'xt-probe')],env)
  if str(root/role/'lib/libX11.6.dylib') not in x.stdout or str(root/role/'lib/libXt.6.dylib') not in t.stdout:raise SystemExit('wrong loaded dylib')
  if role=='old':
   if 'error=not-found' not in x.stdout or 'keysym=0' not in x.stdout or t.returncode==0:raise SystemExit('old negative failed: '+x.stdout+t.stdout)
  elif x.returncode or 'error=moved-message keysym=1234abcd' not in x.stdout or str(root/role/'share/X11/locale') not in x.stdout or 'supports=1' not in x.stdout or t.returncode:raise SystemExit('new default failed: '+x.stdout+t.stdout)
  print(role,'loaded X11/Xt and expected lookup PASS')
 env=e.copy();env['DYLD_LIBRARY_PATH']=str(root/'new/lib');env['XLOCALEDIR']=str(root/'override');env['XKEYSYMDB']=str(root/'keys');(root/'keys').write_text('RelocProbeUnique: 87654321\n');(root/'override').mkdir()
 x=run([str(root/'probe')],env)
 if x.returncode or 'keysym=87654321' not in x.stdout or 'locales='+str(root/'override')+':' not in x.stdout:raise SystemExit('environment override failed: '+x.stdout)
 print('environment overrides PASS')
