#!/usr/bin/env python3
import argparse, os, shutil, subprocess
from pathlib import Path
p=argparse.ArgumentParser()
for name in ('cc','sdk','update-mime-database','new-glib','new-gio','old-glib','old-gio','output'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();root=a.output.resolve();root.mkdir(parents=True,exist_ok=True); sdk=a.sdk.resolve(); here=Path(__file__).resolve().parent
for role, libraries in (('new',(a.new_glib,a.new_gio)),('old',(a.old_glib,a.old_gio))):
 lib=root/role/'lib';lib.mkdir(parents=True,exist_ok=True)
 for src,name in zip(libraries,('libglib-2.0.0.dylib','libgio-2.0.0.dylib')):shutil.copy2(src,lib/name)
for name,mime in (('new','application/x-ember-relocated-unique'),('one','application/x-ember-alpha'),('two','application/x-ember-beta')):
 base=(root/name/'share/mime') if name=='new' else (root/name/'mime');(base/'packages').mkdir(parents=True,exist_ok=True)
 (base/'packages/unique.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info"><mime-type type="'+mime+'"><glob pattern="*.emberunique123"/></mime-type></mime-info>')
 subprocess.run([str(a.update_mime_database),str(base)],env=os.environ|{'XDG_DATA_DIRS':str(base.parent)},check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
exe=root/'mime-regression'
subprocess.run([str(a.cc),'-std=c11','-I'+str(sdk/'include/glib-2.0'),'-I'+str(sdk/'lib/glib-2.0/include'),str(here/'mime-regression.c'),'-L'+str(sdk/'lib'),'-Wl,-rpath,'+str(sdk/'lib'),'-lgio-2.0','-lgobject-2.0','-lglib-2.0','-o',str(exe)],check=True)
one=str(root/'one/mime');two=str(root/'two/mime')
old_env=os.environ.copy();old_env.pop('XDG_DATA_DIRS',None);old_env.pop('GIO_MODULE_DIR',None);old_env['DYLD_LIBRARY_PATH']=str(root/'old/lib')
control=subprocess.run([str(exe),'after',one,two],env=old_env,timeout=30,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
if control.returncode != 1: raise RuntimeError(('old negative control unexpected',control.returncode,control.stderr))
print('old first guess negative PASS')
for mode in ('before','after','threads'):
 env=os.environ.copy();env.pop('XDG_DATA_DIRS',None);env.pop('GIO_MODULE_DIR',None);env['DYLD_LIBRARY_PATH']=str(root/'new/lib')
 subprocess.run([str(exe),mode,one,two],env=env,check=True,timeout=30);print(mode,'PASS')
