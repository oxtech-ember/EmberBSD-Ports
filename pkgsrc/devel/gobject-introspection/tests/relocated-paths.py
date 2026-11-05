#!/usr/bin/env python3
"""Run explicit native GI relocation regression; inputs are real build outputs."""
import argparse, os, pathlib, platform, shutil, subprocess, tempfile
p=argparse.ArgumentParser();p.add_argument('--old-bin',required=True);p.add_argument('--old-lib',required=True);p.add_argument('--new-bin',required=True);p.add_argument('--new-lib',required=True);p.add_argument('--producer-prefix',required=True);a=p.parse_args()
if platform.system() != 'Darwin': raise SystemExit('This fixture requires Darwin and DYLD; use a native ELF fixture on other hosts.')
gir=lambda ns,inc='': ('<?xml version="1.0"?><repository version="1.2" xmlns="http://www.gtk.org/introspection/core/1.0" xmlns:c="http://www.gtk.org/introspection/c/1.0">'+inc+'<namespace name="'+ns+'" version="1.0"/></repository>')
with tempfile.TemporaryDirectory(prefix='gi-relocation-') as temp:
 root=pathlib.Path(temp); env=os.environ.copy()
 for k in ('GI_GIR_PATH','GI_TYPELIB_PATH','DYLD_LIBRARY_PATH','LD_LIBRARY_PATH'):env.pop(k,None)
 env['XDG_DATA_HOME']=str(root/'empty');env['XDG_DATA_DIRS']=str(root/'empty')
 for role,b,l in [('old',a.old_bin,a.old_lib),('new',a.new_bin,a.new_lib)]:
  dest=root/role
  for n in ('bin','lib/girepository-1.0','share/gir-1.0'): (dest/n).mkdir(parents=True)
  for n in ('g-ir-compiler','g-ir-inspect'):shutil.copy2(pathlib.Path(b)/n,dest/'bin'/n)
  shutil.copy2(l,dest/'lib'/pathlib.Path(l).name)
  (dest/'share/gir-1.0/RelocUnique-1.0.gir').write_text(gir('RelocUnique'))
 main=root/'RelocMain-1.0.gir';main.write_text(gir('RelocMain','<include name="RelocUnique" version="1.0"/>'))
 def call(role,tool,args,ok,extra=None,output=None):
  x=env.copy();x['DYLD_LIBRARY_PATH']=str(root/role/'lib');x.update(extra or {})
  r=subprocess.run([str(root/role/'bin'/tool),*args],env=x,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=30)
  if (r.returncode==0)!=ok:raise SystemExit(role+' '+tool+' unexpected status '+str(r.returncode)+'\n'+r.stdout[-2000:])
  if output and output not in r.stdout:raise SystemExit('missing loaded-library proof: '+output)
  print(role,tool,'PASS' if ok else 'expected failure')
 for role in ('old','new'):
  dest=root/role;call(role,'g-ir-compiler',[str(dest/'share/gir-1.0/RelocUnique-1.0.gir'),'-o',str(dest/'lib/girepository-1.0/RelocUnique-1.0.typelib')],True)
 for role,ok in [('old',False),('new',True)]:
  call(role,'g-ir-compiler',[str(main),'-o',str(root/(role+'.typelib'))],ok)
  call(role,'g-ir-inspect',['--print-typelibs','--version=1.0','RelocUnique'],ok,{'DYLD_PRINT_LIBRARIES':'1'},str(root/role/'lib'/pathlib.Path(a.new_lib if role=='new' else a.old_lib).name))
 new=root/'new';old=root/'old';(new/'share/gir-1.0/RelocUnique-1.0.gir').unlink();(new/'lib/girepository-1.0/RelocUnique-1.0.typelib').unlink()
 call('new','g-ir-compiler',[str(main),'-o',str(root/'env.typelib')],True,{'GI_GIR_PATH':str(old/'share/gir-1.0')})
 call('new','g-ir-compiler',['--includedir='+str(old/'share/gir-1.0'),str(main),'-o',str(root/'include.typelib')],True)
 call('new','g-ir-inspect',['--print-typelibs','--version=1.0','RelocUnique'],True,{'GI_TYPELIB_PATH':str(old/'lib/girepository-1.0')})
 prod=pathlib.Path(a.producer_prefix); assert (prod/'share/gir-1.0/GLib-2.0.gir').is_file() and (prod/'lib/girepository-1.0/GLib-2.0.typelib').is_file()
 glib=root/'RelocGLib-1.0.gir';glib.write_text(gir('RelocGLib','<include name="GLib" version="2.0"/>'))
 call('new','g-ir-compiler',[str(glib),'-o',str(root/'glib.typelib')],False)
 call('new','g-ir-inspect',['--print-typelibs','--version=2.0','GLib'],False)
print('relocated paths and override regression PASS')
