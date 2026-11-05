#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check codec provider ownership, versions, checksums and both roles."""
import hashlib, importlib.util, json, tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
owner=Path(__file__).resolve().parents[3]/'pkgsrc/devel/electron44/files'
def load(name,file):
 s=importlib.util.spec_from_file_location(name,owner/file); m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
c=load('electron','build-electron.py'); image=load('image','image-provider.py'); codec=load('codec','codec-provider.py')
with tempfile.TemporaryDirectory() as tmp:
 root=Path(tmp).resolve(); host=root/'host'; target=root/'sysroot/usr/pkg'; view=root/'view'; dbs={'host':{},'target':{}}; inputs={}
 for role,prefix,suffix in (('host',host,'.dylib'),('target',target,'.so')):
  for name,(path,base,minimum,libraries,modules,headers) in codec.EXPAT_PROVIDER.items():
   pkg=prefix/'pkgdb'/(base+'-'+'.'.join(map(str,minimum[:3]))+'nb'+str(minimum[3]));pkg.mkdir(parents=True);dbs[role][path]=[pkg]
   entries=list(headers)+['lib/pkgconfig/'+m+'.pc' for m in modules]+['lib/'+lib+suffix for lib in libraries]
   contents=[]
   for entry in entries:
    f=prefix/entry;f.parent.mkdir(parents=True,exist_ok=True);data=('#define XML_DTD 1\n#define XML_GE 1\n#define XML_NS 1\n#define XML_CONTEXT_BYTES 1024\n' if entry.endswith('expat_config.h') else 'owned');f.write_text(data);contents += [entry,'@comment MD5:'+hashlib.md5(data.encode(),usedforsecurity=False).hexdigest()]
    if role=='host' and entry.endswith('.pc'):
     inputs[str(f)]={};v=view/entry;v.parent.mkdir(parents=True,exist_ok=True);v.write_text('selected')
   (pkg/'+CONTENTS').write_text('\n'.join(contents)+'\n')
   for n in ('+BUILD_INFO','+BUILD_VERSION'): (pkg/n).write_text('owned')
 meta=root/'metadata';meta.mkdir();(meta/'selection.json').write_text(json.dumps({'identity':{'inputs':inputs}}))
 o=SimpleNamespace(shared_expat=True,host_prefix=host,sysroot=root/'sysroot',host_buildlink_pkgsrc=root/'pkgsrc',_common_native_packages=dbs['host'],_common_target_packages=dbs['target'],_compression_catalog={'recipes':{x[0]:{} for x in codec.EXPAT_PROVIDER.values()}})
 native=SimpleNamespace(host={'os':'Darwin'},tool=lambda n:'/selected/'+n)
 sdk={'process':SimpleNamespace(capture=lambda command,env:SimpleNamespace(stdout=('1.0\n'*(len(command)-command.index('--modversion')-1)).encode()))}
 env={'EMBERBSD_ELECTRON_HOST_BUILDLINK_WORK':str(meta)}
 with patch.object(c,'validate_package_source') as verify:
  v=codec.select_expat(image,c,o,sdk,native,env,view);assert verify.call_count==2 and len(env['EMBERBSD_EXPAT_SOURCE_SHA256'])==64
  assert len(v['emberbsd_expat_host_libraries'])==1 and v['emberbsd_expat_target_libraries'][0].endswith('.so')
  f=target/'lib/libexpat.so';f.write_text('altered')
  try:codec.select_expat(image,c,o,sdk,native,env,view)
  except ValueError as error:assert 'differs' in str(error)
  else:raise AssertionError('changed image library accepted')
  f.write_text('owned'); old=dbs['target']['textproc/expat'];dbs['target']['textproc/expat']=[]
  try:codec.select_expat(image,c,o,sdk,native,env,view)
  except ValueError as error:assert 'missing or mismatched' in str(error)
  else:raise AssertionError('missing target accepted')
  dbs['target']['textproc/expat']=old
  header=host/'include/expat.h'; header.write_text('altered')
  try:codec.select_expat(image,c,o,sdk,native,env,view)
  except ValueError as error:assert 'differs' in str(error)
  else:raise AssertionError('changed codec header accepted')
  header.write_text('owned')
  config=host/'include/expat_config.h';oldconfig=config.read_text();newconfig=oldconfig.replace('#define XML_NS 1\n','');config.write_text(newconfig)
  manifest=dbs['host']['textproc/expat'][0]/'+CONTENTS';oldmanifest=manifest.read_text();manifest.write_text(oldmanifest.replace(hashlib.md5(oldconfig.encode(),usedforsecurity=False).hexdigest(),hashlib.md5(newconfig.encode(),usedforsecurity=False).hexdigest()))
  try:codec.select_expat(image,c,o,sdk,native,env,view)
  except ValueError as error:assert 'lacks XML_NS' in str(error)
  else:raise AssertionError('missing Expat namespace support accepted')
  config.write_text(oldconfig);manifest.write_text(oldmanifest)
  pc=view/'lib/pkgconfig/expat.pc';pc.unlink()
  try:codec.select_expat(image,c,o,sdk,native,env,view)
  except ValueError as error:assert 'not selected' in str(error)
  else:raise AssertionError('unselected native codec pkg-config accepted')
print('PASS: codec provider role ownership, checksums and missing dependency rejection')
