#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise GN package floor and binary ownership through selected pkg_info."""
import argparse,importlib.util,subprocess,tempfile
from pathlib import Path
from types import SimpleNamespace
p=argparse.ArgumentParser();p.add_argument('--pkg-info',type=Path,required=True);a=p.parse_args();a.owner=Path(__file__).resolve().parents[3]/'pkgsrc/devel/electron44/files/build-electron.py'
spec=importlib.util.spec_from_file_location('electron_gn',a.owner);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class CommandError(Exception):
 def __init__(self,rc):self.returncode=rc
class Process:
 CommandError=CommandError
 @staticmethod
 def capture(argv,env):
  r=subprocess.run(argv,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  if r.returncode:raise CommandError(r.returncode)
  return r
class Host:
 @staticmethod
 def validate_host_executable(prefix,path,host,search_path):
  assert Path(path)==Path(prefix)/'sbin/pkg_info' and Path(path).is_file()
sdk={'process':Process,'host_prefix':Host};env={'PATH':'/usr/bin:/bin'}
with tempfile.TemporaryDirectory() as d:
 root=Path(d).resolve();(root/'sbin').mkdir();(root/'bin').mkdir();(root/'pkgdb').mkdir();(root/'sbin/pkg_info').symlink_to(a.pkg_info.resolve());(root/'bin/gn').write_text('selected fixture, never executed')
 native=SimpleNamespace(host={'os':'fixture'},path='/bin',tool=lambda name:str(root/'bin'/name));options=SimpleNamespace(host_prefix=root)
 def install(name,owner='devel/gn',file='bin/gn'):
  package=root/'pkgdb'/name;package.mkdir();(package/'+CONTENTS').write_text(f'@name {name}\n@cwd {root}\n{file}\n');(package/'+BUILD_INFO').write_text(f'PKGPATH={owner}\n');return package
 def reject():
  try:m.require_selected_gn(options,sdk,native,env)
  except ValueError:return
  raise AssertionError('invalid selected GN accepted')
 old=install('gn-2610');reject();old.rename(root/'pkgdb'/'gn-2610nb1');package=root/'pkgdb/gn-2610nb1';(package/'+CONTENTS').write_text(f'@name gn-2610nb1\n@cwd {root}\nbin/gn\n');m.require_selected_gn(options,sdk,native,env)
 (package/'+BUILD_INFO').write_text('PKGPATH=foreign/gn\n');reject();(package/'+BUILD_INFO').write_text('PKGPATH=devel/gn\n');(package/'+CONTENTS').write_text(f'@name gn-2610nb1\n@cwd {root}\nbin/other\n');reject()
print('PASS: GN version floor, provider identity and selected executable ownership')
