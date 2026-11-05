#!/usr/bin/env python3
"""Test real Darwin GLib/GIO path defaults with the original prefix present."""
import argparse, os, shlex, shutil, subprocess, time
from pathlib import Path
p=argparse.ArgumentParser()
for name in ('cc','sdk','new-glib','new-gio','new-girepository','old-glib','update-mime-database','output'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args(); root=a.output.resolve(); root.mkdir(parents=True,exist_ok=True);sdk=a.sdk.resolve(); prefix=str(sdk)
probe=root/'probe'; src=Path(__file__).with_name('owned-path-probe.c')
subprocess.run([str(a.cc),'-std=c11','-I'+str(sdk/'include/glib-2.0'),'-I'+str(sdk/'lib/glib-2.0/include'),'-I'+str(sdk/'include/gio-unix-2.0'),'-include','gio/gdesktopappinfo.h',str(src),'-L'+str(sdk/'lib'),'-Wl,-rpath,'+str(sdk/'lib'),'-lgio-2.0','-lgobject-2.0','-lglib-2.0','-o',str(probe)],check=True)
for sub in ('new/lib','old/lib','wrong/unexpected'):(root/sub).mkdir(parents=True,exist_ok=True)
for source, dest in ((a.new_glib,root/'new/lib/libglib-2.0.0.dylib'),(a.new_gio,root/'new/lib/libgio-2.0.0.dylib'),(a.old_glib,root/'old/lib/libglib-2.0.0.dylib'),(a.new_glib,root/'wrong/unexpected/libglib-2.0.0.dylib')):shutil.copy2(source,dest)
env=os.environ.copy()
for k in ('XDG_DATA_DIRS','XDG_CONFIG_DIRS','GIO_LAUNCH_DESKTOP'):env.pop(k,None)
env.update(DYLD_LIBRARY_PATH=str(root/'new/lib'),LC_ALL='en_US.UTF-8',LANGUAGE='zz_TEST')
def run(*args,env=env):
 p=subprocess.run([str(probe),*map(str,args)],env=env,text=True,capture_output=True,timeout=10)
 if p.returncode: raise RuntimeError((args,p.returncode,p.stderr))
 return p.stdout.strip()
def eq(actual,expected):
 if actual!=expected: raise AssertionError((actual,expected))
 print('PASS',actual)
eq(Path(run('loaded')).resolve(),(root/'new/lib/libglib-2.0.0.dylib').resolve())
for fallback,expected in ((prefix+'/share',str(root/'new/share')),(prefix+'/share/../etc',str(root/'new/etc')),(prefix+'/../external',prefix+'/../external'),('/somewhere/locale','/somewhere/locale'),(prefix+'/share:/usr/share',prefix+'/share:/usr/share')):eq(run('resolve','dso','libglib-2.0',fallback),expected)
for anchor,name in (('dso','wrong-library'),('static','libglib-2.0')):eq(run('resolve',anchor,name,prefix+'/share'),prefix+'/share')
wrong=env|{'DYLD_LIBRARY_PATH':str(root/'wrong/unexpected')};eq(run('resolve','dso','libglib-2.0',prefix+'/share',env=wrong),prefix+'/share')
eq(run('xdg'),f'data={root}/new/share\nconfig={root}/new/etc/xdg')
eq(run('xdg',env=env|{'XDG_DATA_DIRS':'/external/a:/external/b','XDG_CONFIG_DIRS':'/external/config'}),'data=/external/a\ndata=/external/b\nconfig=/external/config')
old=env|{'DYLD_LIBRARY_PATH':str(root/'old/lib')};eq(run('xdg',env=old),f'data={sdk}/share\nconfig={sdk}/etc/xdg')
alias=root/'new/share/locale/locale.alias';alias.parent.mkdir(parents=True,exist_ok=True);alias.write_text('zz_TEST fr_FR\n');assert 'fr_FR' in run('alias').splitlines();print('PASS relocated locale.alias')
helper=root/'new/libexec/gio-launch-desktop';helper.parent.mkdir(parents=True,exist_ok=True)
def make_helper(path,marker): path.write_text('#!/bin/sh\nprintf used > '+shlex.quote(str(marker))+'\nexit 0\n');path.chmod(0o755)
desktop=root/'probe.desktop';desktop.write_text('[Desktop Entry]\nType=Application\nName=Probe\nExec=/usr/bin/true\n')
for mode in ('default','override'):
 marker=root/(mode+'-called');marker.unlink(missing_ok=True);custom=root/'override-helper';make_helper(helper,root/'default-called');make_helper(custom,root/'override-called')
 run('launch',desktop,env=env if mode=='default' else env|{'GIO_LAUNCH_DESKTOP':str(custom)})
 for i in range(30):
  if marker.exists():break
  time.sleep(.1)
 assert marker.read_text()=='used';print('PASS GIO helper',mode)

# Exercise the existing Darwin GIO module resolver with the relocated DSO.
module_dir = root / 'new/lib/gio/modules'
module_dir.mkdir(parents=True, exist_ok=True)
module = module_dir / 'libtest.so'
subprocess.run([str(a.cc), '-bundle', '-I' + str(sdk / 'include/glib-2.0'),
                '-I' + str(sdk / 'lib/glib-2.0/include'),
                str(Path(__file__).with_name('gio-module.c')), '-o', str(module)], check=True)
marker = root / 'module-called'
marker.unlink(missing_ok=True)
module_env = env | {'EMBER_GIO_MODULE_MARKER': str(marker)}
module_env.pop('GIO_MODULE_DIR', None)
run('modules', env=module_env)
assert marker.read_text() == 'loaded'
print('PASS relocated GIO module discovery')

# Verify the existing Darwin GIRepository default with its required typelibs.
shutil.copy2(a.new_girepository, root / 'new/lib/libgirepository-2.0.0.dylib')
typelib_dir = root / 'new/lib/girepository-1.0'
typelib_dir.mkdir(parents=True, exist_ok=True)
for name in ('GLib', 'GLibUnix', 'GObject', 'Gio'):
    shutil.copy2(sdk / 'lib/girepository-1.0' / (name + '-2.0.typelib'), typelib_dir)
gi_probe = root / 'typelib-probe'
subprocess.run([str(a.cc), '-std=c11', '-I' + str(sdk / 'include/glib-2.0'),
                '-I' + str(sdk / 'lib/glib-2.0/include'),
                str(Path(__file__).with_name('typelib-probe.c')), '-L' + str(sdk / 'lib'),
                '-Wl,-rpath,' + str(sdk / 'lib'), '-lgirepository-2.0',
                '-lgobject-2.0', '-lglib-2.0', '-o', str(gi_probe)], check=True)
gi_env = env.copy()
gi_env.pop('GI_TYPELIB_PATH', None)
gi_result = subprocess.run([str(gi_probe)], env=gi_env, text=True, capture_output=True, check=True)
if gi_result.stderr or ('search=' + str(typelib_dir)) not in gi_result.stdout or ('loaded=' + str(typelib_dir / 'GLib-2.0.typelib')) not in gi_result.stdout:
    raise AssertionError((gi_result.stdout, gi_result.stderr))
print('PASS relocated GIRepository typelib default')

# GIO supplies its relocated XDG directories to the embedded xdgmime engine.
mime = root / 'new/share/mime'
(mime / 'packages').mkdir(parents=True, exist_ok=True)
(mime / 'packages/unique.xml').write_text(
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">'
    '<mime-type type="application/x-ember-relocated-unique">'
    '<glob pattern="*.emberunique123"/></mime-type></mime-info>')
subprocess.run([str(a.update_mime_database), str(mime)],
               env=env | {'XDG_DATA_DIRS': str(root / 'new/share')}, check=True)
eq(run('mime', env=old), 'application/octet-stream')
eq(run('mime'), 'application/x-ember-relocated-unique')
print('PASS relocated MIME default')
