#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Check selected native Brotli tool against actual stable reads."""
import argparse, hashlib, importlib.util, json, sys, tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
p=argparse.ArgumentParser();p.add_argument('--sdk-source',type=Path,required=True);a=p.parse_args();sys.path.insert(0,str(a.sdk_source.resolve()/'src'))
from emberbsd_sdk import paths
owner=Path(__file__).resolve().parents[3]/'pkgsrc/devel/electron44/files/build-electron.py'
spec=importlib.util.spec_from_file_location('electron',owner);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
spec=importlib.util.spec_from_file_location('stable_fixture',Path(__file__).with_name('stable-read-fixture.py'));f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
with tempfile.TemporaryDirectory() as tmp:
 root=Path(tmp).resolve();host=root/'host';target=root/'target';buildlink=root/'buildlink';export=root/'export';selection=root/'selection';selection.mkdir()
 hp={};tp={};inputs={}
 for pkg,modules in (('archivers/brotli',('libbrotlidec','libbrotlienc')),('archivers/zstd',('libzstd',))):
  name=pkg.split('/')[1]+'-1.0'; e=export/pkg;e.mkdir(parents=True);(e/'distinfo').write_text('verified')
  for prefix,dest in ((host,hp),(target/'usr/pkg',tp)):
   db=prefix/'pkgdb'/name;db.mkdir(parents=True);dest[pkg]=[db]
   entries=['lib/pkgconfig/'+x+'.pc' for x in modules]
   if pkg=='archivers/brotli' and prefix==host:
    tool=host/'bin/brotli';tool.parent.mkdir(parents=True);tool.write_bytes(b'brotli');tool.chmod(0o755)
    entries+=['bin/brotli','@comment MD5:'+hashlib.md5(b'brotli',usedforsecurity=False).hexdigest()]
   (db/'+CONTENTS').write_text('\n'.join(entries))
   if prefix==host:
    for x in modules:inputs[str(host/'lib/pkgconfig'/(x+'.pc'))]={}
 (selection/'selection.json').write_text(json.dumps({'identity':{'inputs':inputs}}))
 options=SimpleNamespace(host_prefix=host,sysroot=target,host_buildlink_pkgsrc=export,_common_native_packages=hp,_common_target_packages=tp)
 sdk={'paths':paths,'process':SimpleNamespace(capture=lambda cmd,env:SimpleNamespace(stdout=b'1\n1\n1\n')),'host_prefix':SimpleNamespace(validate_host_executable=lambda *a,**k:None)}
 native=SimpleNamespace(tool=lambda x:'/selected/'+x,path='/selected',host={'os':'Darwin'})
 env={'EMBERBSD_ELECTRON_HOST_BUILDLINK_WORK':str(selection)}; catalog={'recipes':{'archivers/brotli':{},'archivers/zstd':{}}}
 with patch.object(m,'compression_recipe_catalog',return_value=catalog),patch.object(m,'validate_package_source'),patch.object(m,'platform_protoc_inputs',return_value=[]):
  f.age(tool);m.common_compression(options,sdk,native,env,buildlink)
  f.race(paths,tool,lambda:m.common_compression(options,sdk,native,env,buildlink))
  tool.write_bytes(b'tampered')
  try:m.common_compression(options,sdk,native,env,buildlink)
  except ValueError as error:assert 'differs from installed package' in str(error)
  else:raise AssertionError('Brotli checksum mismatch accepted')
print('PASS: Brotli tool atime, replacement and checksum')
